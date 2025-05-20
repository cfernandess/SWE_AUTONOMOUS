FROM python:3.11-slim

# Set up work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Optional: avoid pip build isolation globally
ENV PIP_NO_BUILD_ISOLATION=1

# Explicitly downgrade setuptools to a known compatible version
RUN pip install --no-cache-dir --upgrade pip setuptools==65.5.1

# Copy the entire repo
COPY . .

# Install Python dependencies for this project
RUN pip install --no-cache-dir -r requirements.txt

# Set the source folder in PYTHONPATH
ENV PYTHONPATH=/app

# Run main (overridden by entrypoint or command args)
ENTRYPOINT ["python", "src/main.py"]

