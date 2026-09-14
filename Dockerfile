FROM python:3.12-slim

ARG BUILD_VERSION=unknown
ARG BUILD_TAG=unknown
ARG BUILD_COMMIT=unknown

LABEL org.opencontainers.image.title="QuantOS"
LABEL org.opencontainers.image.version="$BUILD_VERSION"
LABEL org.opencontainers.image.revision="$BUILD_COMMIT"
LABEL org.opencontainers.image.ref.name="$BUILD_TAG"

WORKDIR /app

COPY backend/ /app/backend/

WORKDIR /app/backend

RUN pip install --no-cache-dir -e .

CMD ["python", "-m", "app.main"]
