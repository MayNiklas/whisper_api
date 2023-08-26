{ lib
, buildPythonPackage

  # propagates
, torch
, fastapi
, multipart
, openai-whisper
, uvicorn

  # tests
, pytestCheckHook
}:

buildPythonPackage {
  pname = "whisper_api";
  version = (lib.strings.removePrefix ''__version__ = "''
    (lib.strings.removeSuffix ''
      "
    ''
      (builtins.readFile ./src/whisper_api/version.py)));
  format = "setuptools";

  src = ./.;

  propagatedBuildInputs = [
    fastapi
    multipart
    openai-whisper
    torch
    uvicorn
  ];

  nativeCheckInputs = [
    pytestCheckHook
  ];

  pythonImportsCheck = [
    "whisper_api"
  ];

  meta = with lib; {
    description = "A simple API for OpenAI's Whisper";
    homepage = "https://github.com/MayNiklas/whisper_api";
    maintainers = with maintainers; [ MayNiklas ];
  };

}
