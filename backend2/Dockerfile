FROM python:3.11-slim

WORKDIR /app

# Install audio system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements manifest and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy repository code
COPY . /app

ENV PYTHONPATH=/app/backend2:/app

EXPOSE 8002

CMD ["uvicorn", "backend2.backend2_service:app", "--host", "0.0.0.0", "--port", "8002"]
