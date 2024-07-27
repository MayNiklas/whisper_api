# newest version:
# https://hub.docker.com/r/nvidia/cuda/tags?page=1&name=-base-ubuntu22.04&ordering=name

ARG CUDA_VERSION=12.4.1
FROM nvidia/cuda:${CUDA_VERSION}-base-ubuntu22.04

ARG PYTHON_VERSION=3.10

WORKDIR /workspace

RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get -qq update && \
    apt-get -qq install --no-install-recommends \
        ffmpeg \
        python${PYTHON_VERSION} \
        python${PYTHON_VERSION}-venv \
        python3-pip && \
    rm -rf /var/lib/apt/lists/* && \
    pip3 install --upgrade pip

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

# disabled by default since GitHub Actions do not have enough space
ARG PREFETCH_MODEL=0
COPY ./src/whisper_api/prefetch.py /tmp/prefetch.py
RUN if [ "$PREFETCH_MODEL" != 0 ]; then \
        python3 /tmp/prefetch.py --model ${PREFETCH_MODEL}; \
    fi; \
    rm /tmp/prefetch.py

COPY . /workspace/code

RUN cd /workspace/code && \
    pip3 install .

ENV PORT=3001 \
    LISTEN=0.0.0.0 \
    LOAD_MODEL_ON_STARTUP=1 \
    DEVELOP_MODE=0

CMD  [ "/usr/local/bin/whisper_api" ]
