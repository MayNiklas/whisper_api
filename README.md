# Whisper API

A simple API to access whisper for speech to text transcription.

It simplifies offloading the heavy lifting of using Whisper to a central GPU server, which can be accessed by multiple people.

## Features

* Transcribes audio files to text using OpenAI Whisper
* Includes a simple static frontend to transcribe audio files (`/`)
* Includes a interactive API documentation using the Swagger UI (`/docs`)
* Uses GPU acceleration if available
* Implements a task queue to handle multiple requests (first in, first out)
* Stateless: to prioritize data privacy, the API only stores data in RAM. Audio files are stored using tempfile and are deleted after processing
* Supports loading the model into VRAM on startup OR on first request
* Supports unloading the model after a certain time of inactivity

## Setup recommendations

This service performs the best, when it is run on a server with a GPU. For using the high-quality models, I recommend using a GPU with at least 12GB of VRAM. The RTX 3060 12GB is most likely the cheapest option for this task.

This service is optimized for a multi user environment. I will discuss 2 setups:

### Personal setup

When you are the only user of this service, you can run it on your local network. This way you can access the service from any device in your network. Use a VPN to access the service from outside your network.

### SMB & research setup

When hosting this service in a more professional environment, we should consider the following:

* should the service be accessible from outside the network?
* who should be able to access the service?

If only users on your local network should be able to access the service and everyone in your network should be able to access it, you can run the service on a server in your network without any further configuration.

If you need to implement access control, I suggest the following:

* use a reverse proxy to terminate SSL
* use oauth2 to only allow users which belong to a certain group to access the service

My setup uses the following software:

* NGINX as a reverse proxy
* Keycloak as an identity provider
* oauth2_proxy to handle oauth2 authentication and session tokens

In case you have some questions about the setup or software, feel free to reach out!

## How to deploy

### Linux - docker

Pre-requisites:

1. have [Docker](https://docs.docker.com/engine/install/) installed
2. install [NVIDIA CUDA](https://developer.nvidia.com/cuda-downloads?target_os=Linux) (if you want to use GPU acceleration)
3. install [NVidia Container Toolkit](https://github.com/NVIDIA/nvidia-container-toolkit) (if you want to use GPU acceleration)

Create the following `compose.yaml` file:

```yaml
services:
  whisperAPI:
    # in production: please specify a current release tag
    image: ghcr.io/mayniklas/whisper_api:main
    ports:
      - "3001:3001"
    environment:
      - PORT=3001
      - LOAD_MODEL_ON_STARTUP=1
      # - UNLOAD_MODEL_AFTER_S=300
      # - DEVELOP_MODE=0
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              capabilities: [gpu]
```

When nop using GPU acceleration, remove the `deploy` section from the `compose.yaml` file.

Run the following commands:

```bash
docker compose up -d
```

You can also use `docker` directly:

```bash
docker run -d -p 3001:3001 --gpus all ghcr.io/mayniklas/whisper_api:main
```

### Linux

Pre-requisites:

1. install [NVIDIA CUDA](https://developer.nvidia.com/cuda-downloads?target_os=Linux)
2. install ffmpeg (e.g. `sudo apt install ffmpeg`)

Since project is a well packaged python project, you don't have to worry about any project specific installation steps.

1. Create a virtual environment
2. Install this project in the virtual environment
3. Create a systemd service that runs the server

### NixOS

Since I'm personally using NixOS, I created a module that is available through this `flake.nix`.

Add the following input to your `flake.nix`:

```nix
{
  inputs = {
    whisper_api.url = "github:MayNiklas/whisper_api";
  };
}
```

Import the module in your `configuration.nix` and use it:

```nix
{ pkgs, config, lib, whisper_api, ... }: {

  imports = [ whisper_api.nixosModules.whisper_api ];

  services.whisper_api = {
    enable = true;
    withCUDA = true;
    loadModelOnStartup = true;
    # unloadModelAfterSeconds = 300;
    listen = "0.0.0.0";
    openFirewall = true;
    environment = { };
  };

}
```

## Development

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

# prepare the environment
pip3 install -e .

# run the server from within the virtual environment
uvicorn whisper_api:app --reload --host 127.0.0.1 --port 3001

# alternatively, you can use the following command to run the server
export PORT=3001
export LISTEN=127.0.0.1
whisper_api
```

### NixOS

```bash
# clone the repository
git clone https://github.com/MayNiklas/whisper_api.git

# change into the directory
cd whisper_api

# run the server via nix (using CUDA)
nix run .#whisper_api_withCUDA

# enter the development shell providing the necessary environment
nix develop .#withCUDA
```

## Settings

| parameter                          | description                                                                               | possible values                                  | default           |
|------------------------------------|-------------------------------------------------------------------------------------------|--------------------------------------------------|-------------------|
| `PORT`                             | Port the API is available under                                                           | any number of port interval                      | 3001              |
| `LISTEN`                           | Address the API is available under                                                        | any IP or domain you own                         | 127.0.0.1         |
| `LOAD_MODEL_ON_STARTUP`            | If model shall be loaded on startup                                                       | `1` (yes) or `0` (no)                            | 1                 |
| `DEVELOP_MODE`                     | Develop mode defaults to smallest model to save time                                      | `1` (yes) or `0` (no)                            | 0                 |
| `UNLOAD_MODEL_AFTER_S`             | If set the model gets unloaded after inactivity of t seconds, unset means no unload       | any int (0 for instant unload)                   | 'unset'           |
| `DELETE_RESULTS_AFTER_M`           | Time after which results are deleted from internal storage                                | any int                                          | 60                |
| `REFRESH_EXPIRATION_TIME_ON_USAGE` | If result is used expand lifetime                                                         | `1` (yes) or `0` (no)                            | 1                 |
| `RUN_RESULT_EXPIRY_CHECK_M`        | Interval in which timeout checks shall be executed                                        | any int (0 enables lazy timeout)                 | 5                 |
| `USE_GPU_IF_AVAILABLE`             | If GPU shall be used when available                                                       | `1` (yes) or `0` (no)                            | 1                 |
| `MAX_MODEL`                        | Max model to be used for decoding, unset means best possible                              | name of official model                           | 'unset'           |
| `MAX_TASK_QUEUE_SIZE`              | The limit of tasks that can be queued in the decoder at the same time before rejection    | any int                                          | 128               |
| `CPU_FALLBACK_MODEL`               | The fallback when `MAX_MODEL` is not set and CPU mode is needed                           | name of official model                           | medium            |
| `LOG_DIR`                          | The directory to store log-file(s) in "" means 'this directory', dir is created if needed | wanted directory name or empty str               | "data/"           |
| `LOG_FILE`                         | The name of the log file                                                                  | arbitrary filename                               | whisper_api.log   |
| `LOG_LEVEL_CONSOLE`                | Level of logging for the console                                                          | "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL") | "INFO"            |
| `LOG_LEVEL_FILE`                   | Level of logging for the file                                                             | "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL") | "INFO"            |
| `LOG_FORMAT`                       | Format of the log messages                                                                | any valid log message format                     | \*see below\*     |
| `LOG_DATE_FORMAT`                  | Format of the date in log messages                                                        | any valid date format                            | "%d.%m. %H:%M:%S" |
| `LOG_ROTATION_WHEN`                | Specifies when log rotation should occur                                                  | "S", "M", "H", "D", "W0"-"W6", "midnight"        | "H"               |
| `LOG_ROTATION_INTERVAL`            | Interval at which log rotation should occur                                               | any int                                          | 2                 |
| `LOG_ROTATION_BACKUP_COUNT`        | Number of backup log files to keep                                                        | any int                                          | 48                |
| `AUTHORIZED_MAILS`                 | Mail-addresses which are authorized to access special routes (whitespace separated)       | any int                                          | 48                |

The log format is: `"[{asctime}] [{levelname}][{processName}][{threadName}][{module}.{funcName}] {message}"`, using `{` as format specifier.
All logging parameters follow pythons [logging](https://docs.python.org/3/library/logging.html) and the [RotatingFileHandler](https://docs.python.org/3/library/logging.handlers.html#timedrotatingfilehandler) specification.

#### LOG_AUTHORIZED_MAILS

The API provides a `/logs` route. That route provides all logs for download.
The verification is done based on the `'X-Email'` field in the request headers.
A valid input would be: `LOG_AUTHORIZED_MAILS="nik@example.com chris@example.com"`.
Requests from localhost are currently always permitted (want an env-option to disable it? - make an issue).

Other privileged routes may come in the future.

#### Note

The system will automatically try to use the GPU and the best possible model when `USE_GPU_IF_AVAILABLE` and `MAX_MODEL` are not set.

###### CPU Mode

`MAX_MODEL` must be set when CUDA is not available or explicitly disabled via `USE_GPU_IF_AVAILABLE`.
`CPU_FALLBACK_MODEL` is the fallback when GPU Mode shall use max-model but CPU shall be limited due to reduced performance.

##### Warning

If `UNLOAD_MODEL_AFTER_S` is set to `0` the model will not only be unloaded nearly instantly, it internally also results in busy waiting!
All ints are assumed to be unsigned.

```bash
# enable development mode -> use small models
export DEVELOP_MODE=1
```

## Projects being used

* [OpenAI Whisper](https://github.com/openai/whisper)
* [PyTorch](https://pytorch.org/)
* [FastAPI](https://fastapi.tiangolo.com/)
