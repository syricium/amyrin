# syntax=docker/dockerfile:1
FROM python:3.10
WORKDIR /bot
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
RUN playwright install chromium
RUN playwright install-deps
COPY . .
CMD ["python3.10", "start.py"]