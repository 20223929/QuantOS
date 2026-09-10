FROM python:3.12-slim

WORKDIR /app

COPY backend/ /app/backend/

WORKDIR /app/backend

RUN pip install --no-cache-dir -e .

CMD ["python", "-m", "app.main"]
