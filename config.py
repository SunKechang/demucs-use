import os
from dotenv import load_dotenv

# 加载.env文件（从项目根目录加载）
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# 新增Cloudflare配置
CLOUDFLARE_ACCOUNT_ID = os.getenv('ACCOUNT_ID')
CLOUDFLARE_DATABASE_ID = os.getenv('CLOUDFLARE_DATABASE_ID')
CLOUDFLARE_API_TOKEN = os.getenv('CLOUDFLARE_API_TOKEN')
R2_ENDPOINT = os.getenv('R2_ENDPOINT')
R2_ACCESS_KEY_ID = os.getenv('R2_ACCESS_KEY_ID')
R2_SECRET_ACCESS_KEY = os.getenv('R2_SECRET_ACCESS_KEY')
R2_BUCKET_NAME = os.getenv('R2_BUCKET_NAME')

LOCAL_STORAGE_PATH = os.getenv('LOCAL_STORAGE_PATH', './local_storage')