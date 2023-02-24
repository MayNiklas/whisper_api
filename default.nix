{ lib
, buildPythonPackage

  # propagates
, torch
, fastapi
, multipart
, openai-whisper
, uvicorn
}:
buildPythonPackage rec {

  pname = "whisper_api";

  # get version from version.py
  version = (lib.strings.removePrefix ''__version__ = "''
    (lib.strings.removeSuffix ''
      "
    ''
      (builtins.readFile ./whisper_api/version.py)));

  src = ./.;

  propagatedBuildInputs = [
    fastapi
    multipart
    openai-whisper
    torch
    uvicorn
  ];

  doCheck = false;

  meta = with lib; {
    description = "A simple API for OpenAI's Whisper";
    homepage = "https://github.com/MayNiklas/whisper_api";
    maintainers = with maintainers; [ MayNiklas ];
  };

}
