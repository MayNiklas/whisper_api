# Whisper API

## How to run

### NixOS

```bash
# clone the repository
git clone https://github.com/MayNiklas/whisper_api.git

# change into the directory
cd whisper_api

# run the server via nix (using CUDA)
nix run .#whisper_api 
```

### Linux

Pre-requisites:

1. install [NVIDIA CUDA](https://developer.nvidia.com/cuda-downloads?target_os=Linux)
2. install ffmpeg (e.g. `sudo apt install ffmpeg`)

```bash
# clone the repository
git clone https://github.com/MayNiklas/whisper_api.git

# change into the directory
cd whisper_api

# create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# install dependencies into the virtual environment
.venv/bin/pip3 install -r requirements.txt

# run the server from within the virtual environment
.venv/bin/uvicorn whisper_api:app --reload --host 127.0.0.1 --port 3001
```

Since Uvicorn is a production server, it is not recommended to use it for development.
Instead, we use the `--reload` flag to enable auto-reloading.

### Linux -  through docker with NVIDIA GPU acceleration

Pre-requisites:

1. Install [docker](https://docs.docker.com/engine/install/).
2. If you have a NVIDIA GPU and want to use it with docker, you need to install [nvidia-docker](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html#docker).

Note: this is not a docker guide! If you are new to docker, please read the [docker documentation](https://docs.docker.com/).
All I can do is provide a few commands, but you should understand what they do.

```bash
# clone the repository
git clone https://github.com/MayNiklas/whisper_api.git

# change into the directory
cd whisper_api

# build the docker image
docker compose build

# run the server (detached)
docker compose up -d

# see the logs
docker compose logs -f

# stop the server
docker compose down

# rebuild the docker image
docker compose build

# force rebuild of the docker image
docker compose build --no-cache
```

The worker will now use the GPU acceleration.
`nvidia-smi` should show the docker container using the GPU.

## Projects being used

* [OpenAI Whisper](https://github.com/openai/whisper)
* [PyTorch](https://pytorch.org/)
* [FastAPI](https://fastapi.tiangolo.com/)
