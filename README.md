# Whisper API

### Development

```sh
# Create a virtual environment
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Install dependencies
pip3 install -r requirements.txt

# Run the server
.venv/bin/uvicorn main:app --reload --host 127.0.0.1 --port 8081
```
