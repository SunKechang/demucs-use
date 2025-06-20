import os
from dotenv import load_dotenv

# 加载.env文件（从项目根目录加载）
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# 新增Cloudflare配置
CLOUDFLARE_ACCOUNT_ID = os.getenv('ACCOUNT_ID')
CLOUDFLARE_DATABASE_ID = os.getenv('CLOUDFLARE_DATABASE_ID')
CLOUDFLARE_API_TOKEN = os.getenv('CLOUDFLARE_ACCOUNT_ID')