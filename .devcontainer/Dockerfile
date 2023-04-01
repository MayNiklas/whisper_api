# FROM mcr.microsoft.com/devcontainers/base:ubuntu
FROM nvidia/cuda:11.7.0-base-ubuntu22.04

RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get -qq update && \
    apt-get -qq install --no-install-recommends \
        curl \
        ffmpeg \
        git \
        nvtop \
        python3 \
        python3-pip \
        python3-setuptools \
        python3-venv \
        python3-wheel \
        software-properties-common \
        wget

COPY requirements.txt /tmp/requirements.txt

RUN pip3 install --upgrade pip && \
    pip3 install -r  /tmp/requirements.txt

RUN python3 whisper_api/download_models.py

CMD git config --global --add safe.directory /workspaces/whisper_api
