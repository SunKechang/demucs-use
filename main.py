import os
import tempfile
import shutil
import zipfile
from flask import Flask, request, send_file, after_this_request
from demucs import separate
from config import ROOT_STORAGE_PATH
import uuid

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

@app.route('/api/separate', methods=['POST'])
def handle_separation():
    # 检查文件是否上传
    if 'file' not in request.files:
        return '未提供文件', 400
    
    file = request.files['file']
    if file.filename == '':
        return '未选择文件', 400
    
    # 替换临时目录创建逻辑
    session_id = f"sep_{uuid.uuid4().hex}"
    storage_dir = os.path.join(ROOT_STORAGE_PATH, session_id)
    os.makedirs(storage_dir, exist_ok=True)
    
    # 安全处理文件名
    from werkzeug.utils import secure_filename
    safe_filename = secure_filename(file.filename or "default_file")
    input_path = os.path.join(storage_dir, safe_filename)
    output_dir = os.path.join(storage_dir, "separated")
    
    # 保存上传文件
    file.save(input_path)
    
    # 执行音频分离
    separate_audio(input_path, output_dir)
    
    # 构建结果路径映射
    result_paths = {}
    model_dir = os.path.join(output_dir, "htdemucs")
    model_dir = os.path.join(model_dir, "input")
    print("----------")
    print(model_dir)
    if os.path.exists(model_dir):
        for track in ['drum', 'vocals', 'bass', 'other']:
            track_path = os.path.join(model_dir, f"{track}.wav")
            if os.path.exists(track_path):
                rel_path = os.path.relpath(track_path, start=storage_dir)
                # 转换路径分隔符为统一的正斜杠
                result_paths[track] = rel_path.replace('\\', '/')
    # 返回JSON格式结果
    from flask import jsonify
    # 修改返回数据中的uuid字段为session_id
    return jsonify({
        "status": "success",
        "session_id": session_id,  # 修改字段名更语义化
        "tracks": result_paths
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)