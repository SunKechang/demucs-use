pip install pipreqs
pipreqs . --force
docker build -t demucs-service .
docker run -d -p 9000:9000 --name demucs demucs-service