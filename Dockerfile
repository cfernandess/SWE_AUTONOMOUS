FROM python:3.11-slim

# Set up work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire repo
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Default command (overridden by ENTRYPOINT script)
# Set the source folder in PYTHONPATH
ENV PYTHONPATH=/app

CMD ["python", "src/main.py"]
