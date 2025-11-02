# Use a Python 3.9.6 Alpine base image
FROM python:3.11.1-slim

# Set the working directory
WORKDIR /app

# Copy all files from the current directory to the container's /app directory
COPY . .

# Install necessary dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    build-essential \
    libffi-dev \
    ffmpeg \
    aria2 \
    && rm -rf /var/lib/apt/lists/*

# Make mp4decrypt executable and set proper permissions
RUN chmod +x /app/tools/mp4decrypt

# Install Python dependencies
RUN pip3 install --no-cache-dir --upgrade pip \
    && pip3 install --no-cache-dir --upgrade -r ugbots.txt \
    && python3 -m pip install -U yt-dlp

# Set the command to run the application
CMD ["sh", "-c", "gunicorn app:app & python3 main.py"]
