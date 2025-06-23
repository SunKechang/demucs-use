# 使用单个Debian构建阶段
FROM registry.cn-hangzhou.aliyuncs.com/library/python:3.10-slim

WORKDIR /app
COPY requirements.txt .

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip install demucs -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --extra-index-url https://download.pytorch.org/whl/cpu

COPY . .

EXPOSE 9000
CMD ["python", "main.py"]