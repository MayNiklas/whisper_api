# newest version:
# https://hub.docker.com/r/nvidia/cuda/tags?page=1&name=-base-ubuntu24.04&ordering=name

ARG CUDA_VERSION=13.0.1
FROM nvidia/cuda:${CUDA_VERSION}-base-ubuntu24.04

WORKDIR /workspace

RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get -qq update && \
    apt-get -qq install --no-install-recommends \
        ffmpeg \
        python3 \
        python3-venv \
        python3-pip && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt --break-system-packages

# disabled by default since GitHub Actions do not have enough space
ARG PREFETCH_MODEL=0
COPY ./src/whisper_api/prefetch.py /tmp/prefetch.py
RUN if [ "$PREFETCH_MODEL" != 0 ]; then \
        python3 /tmp/prefetch.py --model ${PREFETCH_MODEL}; \
    fi; \
    rm /tmp/prefetch.py

COPY . /workspace/code

RUN cd /workspace/code && \
    pip install --no-cache-dir . --break-system-packages

ENV PORT=3001 \
    LISTEN=0.0.0.0 \
    LOAD_MODEL_ON_STARTUP=1 \
    DEVELOP_MODE=0

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
    CMD python3 -c "import urllib.request, os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/api/v1/decoder_status')" || exit 1

CMD  [ "/usr/local/bin/whisper_api" ]
