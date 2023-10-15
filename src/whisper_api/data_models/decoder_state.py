from pydantic import BaseModel
from whisper_api.data_models.data_types import model_sizes_str_t


class DecoderState(BaseModel):
    """ Represents a state update from the decoder """
    gpu_mode: bool = None
    max_model_to_use: str = None
    last_loaded_model_size: model_sizes_str_t = None
    is_model_loaded: bool = None
    tasks_in_queue: int = None
