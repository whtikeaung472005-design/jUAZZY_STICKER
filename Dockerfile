# Filename: Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# OS Hack: Force Linux to prefer IPv4 over IPv6 to fix 'Network is unreachable' error
RUN echo "precedence ::ffff:0:0/96  100" >> /etc/gai.conf

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

CMD ["python", "main.py"]
