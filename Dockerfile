FROM python:3.11-slim

# Cài đặt thư viện cần thiết và driver SQL Server
RUN apt-get update && \
    apt-get install -y \
    unixodbc \
    unixodbc-dev \
    curl \
    gnupg2 \
    apt-transport-https

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=app.py
ENV FLASK_ENV=production

CMD ["flask", "run", "--host=0.0.0.0"]
