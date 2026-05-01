FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create transcripts directory
RUN mkdir -p /app/transcripts

# Expose port
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]


