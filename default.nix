{ lib
, fetchFromGitHub
, buildPythonPackage

  # propagates
, torch
, fastapi
, multipart
, openai-whisper
, typing-extensions
, uvicorn

  # tests
, pytestCheckHook
, unittestCheckHook
}:

buildPythonPackage rec {
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
    # # https://github.com/elarivie/pyReaderWriterLock
    # (buildPythonPackage rec {
    #   pname = "pyReaderWriterLock";
    #   version = "1.0.9";
    #   src = fetchFromGitHub {
    #     owner = "elarivie";
    #     repo = pname;
    #     rev = "e7382855cdd46c9d54b2d697c48c00b8fd7e4c81";
    #     hash = "sha256-53LOAUzfiD61MNik+6XnyEslfK1jJkWDElnvIbgHqDU=";
    #   };
    #   propagatedBuildInputs = [ typing-extensions ];
    #   nativeCheckInputs = [
    #     unittestCheckHook
    #   ];
    # })
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
