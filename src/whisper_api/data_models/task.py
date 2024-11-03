import datetime as dt
import io
import re
from tempfile import NamedTemporaryFile
from typing import Any
from uuid import uuid4

from pydantic import BaseModel
from whisper.utils import WriteSRT

from whisper_api.data_models.data_types import model_sizes_str_t
from whisper_api.data_models.data_types import named_temp_file_name_t
from whisper_api.data_models.data_types import status_str_t
from whisper_api.data_models.data_types import task_type_str_t
from whisper_api.data_models.data_types import uuid_hex_t
from whisper_api.log_setup import uuid_log_format


class PrivacyAwareTaskBaseModel(BaseModel):
    """BaseModel that doesn't print full uuids when in privacy mode"""

    def __str__(self):
        """gets the __str__ of the BaseModel in injects uuid obfuscation if needed"""
        original_repr = super().__str__()

        # regex pattern to extract the UUID
        pattern = r"uuid='([a-f0-9\-]+)'"

        # search for the pattern in the repr string
        match = re.search(pattern, original_repr)

        # check if a match was found
        if not match:
            return original_repr

        old_uuid = match.group(1)
        # convert uuid
        new_uuid = uuid_log_format(old_uuid)

        # replace old uuid with new uuid in the string
        new_repr = re.sub(pattern, f"uuid='{new_uuid}'", original_repr)
        return new_repr

    def __repr__(self):
        """rebuild the BaseModel repr but with potential uuid obfuscation"""
        return f"{self.__class__.__name__}({self.__str__()})"


class TaskResponse(BaseModel):
    """The class that is returned via the API"""

    task_id: str
    task_type: task_type_str_t
    status: str
    time_uploaded: dt.datetime
    transcript: str | None = None
    source_language: str | None = None
    position_in_queue: int | None = None
    processing_duration: int | None = None
    time_processing_finished: dt.datetime | None = None
    target_model_size: str | None = None
    used_model_size: str | None = None
    used_device: str | None = None


class WhisperResult(BaseModel):
    """The result of a whisper translation/ transcription plus additional information"""

    text: str
    language: str  # spoken language
    output_language: str  # language code of the output language (hopefully)  # TODO validate that always true
    segments: list[dict[str, float | str | int | list[int]]]
    used_model_size: model_sizes_str_t
    start_time: dt.datetime
    end_time: dt.datetime
    used_device: str

    @property
    def processing_duration_s(self) -> int:
        return (self.end_time - self.start_time).seconds

    def get_srt_buffer(self) -> io.StringIO:
        """The result text in SRT format"""
        # setup buffer
        buffer = io.StringIO()
        # ResultWriter base-class requires an output directory
        # but WriteSRT's write_result function doesn't use it, it prints straight to the given buffer
        srt_writer = WriteSRT("/tmp")

        # trigger writing
        srt_writer.write_result(self.__dict__, buffer)

        # reset file pointer to the beginning of file
        buffer.seek(0)

        return buffer


class Task(BaseModel):
    audiofile_name: named_temp_file_name_t
    task_type: task_type_str_t

    status: status_str_t = "pending"
    source_language: str | None = None
    position_in_queue: int | None = None
    whisper_result: WhisperResult | None = None
    time_uploaded: dt.datetime | None = None
    uuid: uuid_hex_t | None = None
    target_model_size: model_sizes_str_t | None = None
    original_file_name: str = "unknown"
    used_device: str = "unknown"

    def model_post_init(self, context: Any):
        self.uuid = self.uuid or uuid4().hex
        self.time_uploaded = self.time_uploaded or dt.datetime.now()

    @property
    def to_transmit_full(self) -> TaskResponse:
        # TODO extract that list to a better place
        if self.status in ["pending", "processing", "failed"]:
            return TaskResponse(
                task_id=self.uuid,
                time_uploaded=self.time_uploaded,
                status=self.status,
                position_in_queue=self.position_in_queue,
                task_type=self.task_type,
            )

        # task status = "finished"
        return TaskResponse(
            task_id=self.uuid,
            transcript=self.whisper_result.text,
            source_language=self.whisper_result.language,
            task_type=self.task_type,
            status=self.status,
            position_in_queue=self.position_in_queue,
            time_uploaded=self.time_uploaded,
            processing_duration=self.whisper_result.processing_duration_s,
            time_processing_finished=self.whisper_result.end_time,
            target_model_size=self.target_model_size,
            used_model_size=self.whisper_result.used_model_size,
            used_device=self.whisper_result.used_device,
        )

    @property
    def to_json(self) -> dict:
        json_cls = {
            **self.__dict__,
            "whisper_result": self.whisper_result.__dict__ if self.whisper_result else None,
            "audiofile_name": self.audiofile_name,
        }

        return json_cls

    @staticmethod
    def from_json(serialized_task: dict) -> "Task":
        """Create a Task object from a json dict"""
        whisper_result = serialized_task["whisper_result"]
        json_cls = {
            **serialized_task,
            "whisper_result": WhisperResult(**whisper_result) if whisper_result else None,
            "audiofile_name": serialized_task["audiofile_name"],
        }

        return Task(**json_cls)


if __name__ == "__main__":
    t = Task(audiofile_name=NamedTemporaryFile().name, source_language="en", task_type="transcribe")
    t.whisper_result = WhisperResult(
        text="hello",
        language="en",
        output_language="de",
        segments=[],
        used_model_size="medium",
        start_time=dt.datetime.now(),
        end_time=dt.datetime.now(),
        used_device="gpu",
    )
    serialized = t.to_json
    new_task = Task.from_json(serialized)

    print(new_task)
    print(t == new_task)
