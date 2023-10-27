# Whisper API

A simple whisper api for speech to text.
Work in progress.

## How to run

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

### NixOS

```bash
# clone the repository
git clone https://github.com/MayNiklas/whisper_api.git

# change into the directory
cd whisper_api

# run the server via nix (using CUDA)
nix run .#whisper_api
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

The log format is: `"[{asctime}] [{levelname}][{processName}][{threadName}][{module}.{funcName}] {message}"`, using `{` as format specifier.
All logging parameters follow pythons [logging](https://docs.python.org/3/library/logging.html) and the [RotatingFileHandler](https://docs.python.org/3/library/logging.handlers.html#timedrotatingfilehandler) specification.

#### Note
The system will automatically try to use the GPU and the best possible model when `USE_GPU_IF_AVAILABLE` and `MAX_MODEL` are not set.
###### CPU Mode
`MAX_MODEL` must be set when CUDA is not available or explicitly disabled via `USE_GPU_IF_AVAILABLE`.
`CPU_FALLBACK_MODEL` is the fallback when GPU Mode shall use max-model but CPU shall be limited due to reduced performance.

##### Warning:
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
