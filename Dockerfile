FROM python:3.8-slim-buster AS builder

RUN apt update && apt install -y \
  gcc \
  g++ \
  libfreetype6-dev \
  pkg-config

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.8-slim-buster AS dev

COPY --from=builder /usr/local/lib/python3.8/site-packages/ /usr/local/lib/python3.8/site-packages
