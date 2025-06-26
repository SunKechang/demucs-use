FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
RUN pip install -r requirements.txt \
    && pip install demucs \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    && pip install librosa

COPY . .

EXPOSE 9000
CMD ["python", "main.py"]