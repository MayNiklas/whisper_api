from typing import Literal

uuid_hex_t = str
task_type_str_t = Literal["transcribe", "translate"]
status_str_t = Literal["pending", "processing", "finished", "failed"]
model_sizes_str_t = Literal["base", "small", "medium", "large"]
named_temp_file_name_t = str
