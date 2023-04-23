from typing import Literal

uuid_hex_t = str
task_type_str_t = Literal["transcribe", "translate"]
status_str_t = Literal["pending", "processing", "finished"]
model_sizes_str_t = Literal["base", "small", "medium", "large"]