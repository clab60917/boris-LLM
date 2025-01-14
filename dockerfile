# Use Ubuntu as base image
FROM ubuntu:22.04

# Install required packages
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Copy application files
COPY main.py .

# Create necessary directories and files
RUN mkdir -p logs results \
    && touch tests.py test_script.py

# Commande par défaut
CMD ["python3", "-u", "main.py"]