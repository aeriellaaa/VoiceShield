FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for audio processing (ffmpeg, libsndfile)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements manifest and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy repository code
COPY . /app

EXPOSE 8000

CMD ["uvicorn", "ml.api.detection_service:app", "--host", "0.0.0.0", "--port", "8000"]
