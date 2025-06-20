import os
from flask import Flask, request, jsonify
from demucs import separate
from threading import Thread
import time, json

app = Flask(__name__)

def separate_audio(input_path, output_dir):
    """
    使用Demucs分离音频并将结果保存到输出目录
    
    参数:
        input_path (str): 输入音频文件路径
        output_dir (str): 输出目录
    """
    os.makedirs(output_dir, exist_ok=True)
    separate.main([input_path, '-o', output_dir])
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

def process_single_task(task, conn):
    cursor = None
    try:
        # 原子化更新任务状态
        updated = update_task_status(task['id'], 'waiting', 'processing', conn)
        if updated == 0:
            print(f"任务{task['id']}已被其他worker处理")
            return

        cursor = conn.cursor(dictionary=True)
        output_path_prefix = "separated"
        input_path = os.path.join(str(""), task['file_path'])
        output_dir = os.path.join(os.path.dirname(input_path), output_path_prefix)
        
        # 使用正确的输入路径
        filepath = os.path.join(input_path, task['file_name'])
        separate_audio(filepath, output_dir)
        
        result_path = {
            "drum": f"/{output_path_prefix}/htdemucs/drum.wav",
            "vocals": f"/{output_path_prefix}/htdemucs/vocals.wav",
            "bass": f"/{output_path_prefix}/htdemucs/bass.wav",
            "other": f"/{output_path_prefix}/htdemucs/other.wav"
        }
        
        # 更新任务状态
        cursor.execute(
            "UPDATE tasks SET status = 'ended', result_path = %s WHERE id = %s",
            (json.dumps(result_path), task['id'])
        )
        conn.commit()
        
    except Exception as e:
        print(f"任务处理失败: {e}")
        if cursor:
            cursor.execute("UPDATE tasks SET status = 'failed' WHERE id = %s", (task['id'],))
    finally:
        if cursor:
            cursor.close()

def task_worker():
    """D1数据库任务处理工作线程"""
    import requests
    from config import (  # 新增导入
        CLOUDFLARE_ACCOUNT_ID,
        CLOUDFLARE_DATABASE_ID,
        CLOUDFLARE_API_TOKEN
    )
    
    while True:
        try:
            # 从config获取配置
            account_id = CLOUDFLARE_ACCOUNT_ID
            database_id = CLOUDFLARE_DATABASE_ID
            api_token = CLOUDFLARE_API_TOKEN
            
            # 构建D1 API请求
            url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/d1/database/{database_id}/query"
            headers = {
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "sql": "SELECT * FROM tasks WHERE status = ? AND is_deleted = ?;",
                "params": ["waiting", "0"]
            }
            print(url)
            # 发送请求
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            # 解析响应
            result = response.json().get('result', [{}])[0]
            print(result)
            if result.get('success'):
                tasks = result.get('results', [])
                # if tasks:
                #     print(f"发现{len(tasks)}个等待处理的任务")
                #     for task in tasks:
                #         process_single_task(task, None)  # 需要调整process_single_task参数
            else:
                print("D1查询失败:", result.get('errors'))
                
        except Exception as err:
            print(f"API请求异常: {err}")
        finally:
            time.sleep(3)

# 在应用启动时启动工作线程（添加到文件底部）
if __name__ == '__main__':
    Thread(target=task_worker, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=True)