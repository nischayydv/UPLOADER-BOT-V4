FROM python:3.9-slim

WORKDIR /app

# Install system packages: ffmpeg, jq, python3-dev, git (REQUIRED for GitHub pip installs)
RUN apt-get update && \
    apt-get install -y ffmpeg jq python3-dev git && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all app files
COPY . .

# Expose port (for Flask/Rander)
EXPOSE 8080

# Start the bot
CMD ["python3", "bot.py"]
