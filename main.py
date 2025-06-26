import os
from flask import Flask, request, jsonify
from demucs import separate
from threading import Thread
import time, json
import requests
from config import (
    R2_ENDPOINT, 
    R2_ACCESS_KEY_ID, 
    R2_SECRET_ACCESS_KEY, 
    R2_BUCKET_NAME,
    LOCAL_STORAGE_PATH
)
import boto3

app = Flask(__name__)

def separate_audio(input_path, output_dir):
    """
    使用Demucs分离音频并将结果保存到输出目录
    
    参数:
        input_path (str): 输入音频文件路径
        output_dir (str): 输出目录
    """
    os.makedirs(output_dir, exist_ok=True)
    # 添加绝对路径处理
    abs_input = os.path.abspath(input_path)
    print(f"分离绝对路径：{abs_input}")
    separate.main([
        abs_input,  # 使用绝对路径
        '-o', output_dir,
        '-n', 'htdemucs',
        '-d', 'cuda'  # 新增GPU支持参数
    ])
    print(f"音频分离完成，结果保存在 {output_dir}")

def handle_separation():
    if 'file' not in request.files:
        return jsonify({'error': '未提供文件'}), 400  # 使用jsonify包装响应
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400  # 使用jsonify包装响应

# 修复未定义变量问题
def update_task_status(task_id: int, from_status: str, to_status: str, conn) -> int:
    """原子化更新任务状态"""
    cursor = None
    try:
        cursor = conn.cursor()
        # 使用条件更新确保状态一致性
        cursor.execute(
            "UPDATE tasks SET status = %s WHERE id = %s AND status = %s",
            (to_status, task_id, from_status)
        )
        conn.commit()
        return cursor.rowcount
    finally:
        if cursor:
            cursor.close()

def process_single_task(task):
    try:
        # 初始化R2客户端
        s3 = boto3.client(
            service_name="s3",
            endpoint_url=R2_ENDPOINT,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            region_name="auto"
        )
        # 构建存储路径（新增文件名处理）
        original_filename = task['file_name']
        filename_without_ext = os.path.splitext(original_filename)[0]
        task_storage_dir = os.path.join(LOCAL_STORAGE_PATH, filename_without_ext)
        os.makedirs(task_storage_dir, exist_ok=True)
        
        # 完整本地路径
        local_path = os.path.join(task_storage_dir, original_filename)
        
        # 下载文件（保持原有逻辑）
        s3.download_file(R2_BUCKET_NAME, original_filename, local_path)
        print(f"文件下载完成：{local_path}")

        # 创建分离结果目录（新增输出路径）
        output_dir = os.path.join(task_storage_dir, "separated")
        
        # 执行音频分离（修改输入路径）
        separate_audio(local_path, output_dir)
        print(f"分离结果存储于：{output_dir}")
        
        # 分离结果路径
        separated_dir = os.path.join(output_dir, "htdemucs", filename_without_ext)
        
        # 上传分离结果到R2并构建结果映射
        result_mapping = {}
        for track in ['bass', 'drums', 'other', 'vocals']:
            local_file = os.path.join(separated_dir, f"{track}.wav")
            r2_filename = f"{filename_without_ext}-{track}.wav"
            # 上传到R2
            s3.upload_file(
                Filename=local_file,
                Bucket=R2_BUCKET_NAME,
                Key=r2_filename
            )
            result_mapping[track] = r2_filename
        print(result_mapping)
        update_sql = "UPDATE tasks SET status = 'completed', result = ?WHERE id = ?"
        update_params = [json.dumps(result_mapping), task['id']]
        update_result = execute_d1_query(update_sql, update_params)
        if not update_result.get('success'):
            print("状态更新失败:", update_result.get('errors'))

    except Exception as e:
        print(f"文件处理失败: {e}")
        # 使用execute_d1_query标记失败状态
        execute_d1_query(
            "UPDATE tasks SET status = 'failed' WHERE id = ?",
            [task['id']]
        )


from config import (
    CLOUDFLARE_ACCOUNT_ID,
    CLOUDFLARE_DATABASE_ID,
    CLOUDFLARE_API_TOKEN
)    
def execute_d1_query(sql: str, params: list) -> dict:
        """执行D1数据库查询/更新（新增函数）"""
        try:
            response = requests.post(
                f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/d1/database/{CLOUDFLARE_DATABASE_ID}/query",
                headers={
                    "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
                    "Content-Type": "application/json"
                },
                json={
                    "sql": sql,
                    "params": params
                }
            )
            response.raise_for_status()
            return response.json()['result'][0]
        except Exception as e:
            print(f"D1请求异常: {e}")
            return {'success': False, 'errors': [str(e)]}

def task_worker():
    """D1数据库任务处理工作线程"""
    
    while True:
        try:
            # 使用新函数执行查询
            query_result = execute_d1_query(
                "SELECT * FROM tasks WHERE status = ? AND is_deleted = ?;",
                ["waiting", "0"]
            )
            if query_result.get('success'):
                tasks = query_result.get('results', [])
                for task in tasks:
                    # 使用新函数执行状态更新
                    update_result = execute_d1_query(
                        "UPDATE tasks SET status = ? WHERE id = ? AND status = ?;",
                        ["processing", task['id'], "waiting"]
                    )
                    if update_result.get('meta', {}).get('rows_written', 0) > 0:
                        print(f"开始处理任务 {task['id']}")
                        process_single_task(task)
                    else:
                        print(f"跳过已被处理的任务 {task['id']}")
                
        except Exception as err:
            print(f"API请求异常: {err}")
        finally:
            time.sleep(3)

@app.route('/process_task/<int:task_id>', methods=['POST'])
def handle_manual_process(task_id):
    """手动触发任务处理接口（新增）"""
    try:
        # 原子化状态更新
        update_result = execute_d1_query(
            "UPDATE tasks SET status = ? WHERE id = ? AND status = ?",
            ["processing", task_id, "waiting"]
        )
        
        if update_result.get('meta', {}).get('rows_written', 0) > 0:
            # 获取完整任务信息
            query_result = execute_d1_query(
                "SELECT * FROM tasks WHERE id = ? AND is_deleted = ?",
                [task_id, "0"]
            )
            
            if query_result.get('success') and query_result.get('results'):
                task = query_result['results'][0]
                process_single_task(task)
                return jsonify({"status": "processing_started", "task_id": task_id})
            
        return jsonify({"error": "task_not_available"}), 400
        
    except Exception as e:
        print(f"手动处理异常: {e}")
        return jsonify({"error": str(e)}), 500

# 在应用启动时启动工作线程
if __name__ == '__main__':
    # Thread(target=task_worker, daemon=True).start()
    app.run(host='0.0.0.0', port=9000, debug=True)

# 在文件开头添加验证代码
import torch
print(f"CUDA 可用状态: {torch.cuda.is_available()}")
print(f"当前设备: {torch.cuda.get_device_name(0)}")