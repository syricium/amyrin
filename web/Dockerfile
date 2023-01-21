# syntax=docker/dockerfile:1
FROM python:3.10-alpine
WORKDIR /webserver
COPY requirements.txt requirements.txt
COPY package.json package.json
RUN apk add nodejs npm
RUN pip install -r requirements.txt
EXPOSE 5000
COPY . .
RUN npm i
RUN npm rebuild
RUN npm run build
CMD ["python3.10", "app.py"]