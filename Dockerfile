FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY sql ./sql
COPY src ./src
ENV PYTHONUTF8=1
CMD ["python", "src/run_pipeline.py"]
