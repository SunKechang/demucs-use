import os
from dotenv import load_dotenv

# 加载.env文件（从项目根目录加载）
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# 获取配置（保持向后兼容）
ROOT_STORAGE_PATH = os.path.abspath(
    os.environ.get('DEMUCS_STORAGE_PATH', './storage')
)

# 自动创建存储目录（保留原逻辑）
os.makedirs(ROOT_STORAGE_PATH, exist_ok=True)