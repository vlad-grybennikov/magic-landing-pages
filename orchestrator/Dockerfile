FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 mlp

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir torch==2.13.0 torchvision==0.28.0 \
        --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir open_clip_torch==3.3.0 pillow==12.3.0

COPY --chown=mlp:mlp . .

ARG RELEASE=dev
ARG COMMIT=unknown
ENV HF_HOME=/models \
    PYTHONUNBUFFERED=1 \
    MLP_RELEASE=${RELEASE} \
    MLP_COMMIT=${COMMIT}
RUN mkdir -p /models && chown mlp:mlp /models
VOLUME ["/models"]
USER mlp

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=5 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
