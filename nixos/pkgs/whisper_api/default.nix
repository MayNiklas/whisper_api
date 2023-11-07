{ self
, lib
, buildPythonPackage

  # propagates
, torch
, fastapi
, multipart
, openai-whisper
, uvicorn
, ffmpeg-python

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
    multipart
    openai-whisper
    torch
    uvicorn
  ];

  nativeCheckInputs = [ pytestCheckHook ];

  pythonImportsCheck = [ "whisper_api" ];

  meta = with lib; {
    description = "A simple API for OpenAI's Whisper";
    homepage = "https://github.com/MayNiklas/whisper_api";
    maintainers = with maintainers; [ MayNiklas ];
  };

}
