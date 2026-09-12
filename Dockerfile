FROM python:3.11-slim

WORKDIR /app

# Install system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create persistent storage directories
RUN mkdir -p data chroma_db knowledge

# Expose web ports
EXPOSE 7860
EXPOSE 8000

ENV UI_HOST=0.0.0.0
ENV UI_PORT=7860
ENV PORT=7860

CMD ["python", "app.py"]
