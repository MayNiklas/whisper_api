# newest version:
# https://hub.docker.com/r/nvidia/cuda/tags?page=1&name=-base-ubuntu22.04&ordering=name

FROM nvidia/cuda:12.4.1-base-ubuntu22.04

ENV PYTHON_VERSION=3.10

WORKDIR /workspace

RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get -qq update && \
    apt-get -qq install --no-install-recommends \
        ffmpeg \
        python${PYTHON_VERSION} \
        python${PYTHON_VERSION}-venv \
        python3-pip && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . /workspace/code

RUN cd /workspace/code && \
    pip3 install .

ENV PORT=3001 \
    LISTEN=0.0.0.0 \
    LOAD_MODEL_ON_STARTUP=1 \
    DEVELOP_MODE=0

CMD  [ "/usr/local/bin/whisper_api" ]
