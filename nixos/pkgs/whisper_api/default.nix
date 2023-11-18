{ self
, lib
, buildPythonPackage

  # propagates
, fastapi
, ffmpeg-python
, multipart
, openai-triton
, openai-whisper
, torch
, uvicorn

  # tests
, pytestCheckHook

, cudaSupport ? false
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
    (openai-whisper.override { torch = torch.override { inherit cudaSupport; openai-triton = openai-triton.override { inherit cudaSupport; }; }; })
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
