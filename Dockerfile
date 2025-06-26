FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y ffmpeg jq python3-dev build-essential libffi-dev libssl-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN cat requirements.txt && pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python3", "bot.py"]
