{ self
, lib
, buildPythonPackage

  # propagates
, fastapi
, ffmpeg-python
, httpx
, openai-whisper
, python-multipart
, uvicorn

  # tests
, pytestCheckHook
}:
buildPythonPackage {

  pname = "whisper_api";
  version = (lib.strings.removePrefix ''__version__ = "'' (lib.strings.removeSuffix ''
    "
  ''
    (builtins.readFile "${self}/src/whisper_api/version.py")));

  format = "setuptools";
  src = self;

  propagatedBuildInputs = [
    fastapi
    ffmpeg-python
    httpx
    openai-whisper
    python-multipart
    uvicorn
  ];

  # nativeCheckInputs = [ pytestCheckHook ];

  pythonImportsCheck = [ "whisper_api" ];

  meta = with lib; {
    description = "A simple API for OpenAI's Whisper";
    homepage = "https://github.com/MayNiklas/whisper_api";
    maintainers = with maintainers; [ MayNiklas ];
  };

}
