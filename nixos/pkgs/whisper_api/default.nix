{ self
, lib
, python3
,
}:
let
  version = (lib.strings.removePrefix ''__version__ = "'' (lib.strings.removeSuffix ''
    "
  ''
    (builtins.readFile "${self}/src/whisper_api/version.py")));
in
python3.pkgs.buildPythonApplication {

  pname = "whisper_api";
  inherit version;

  pyproject = true;
  src = self;

  nativeBuildInputs = with python3.pkgs; [ setuptools ];

  propagatedBuildInputs = with python3.pkgs; [
    fastapi
    ffmpeg-python
    openai-whisper
    python-multipart
    uvicorn
  ];

  nativeCheckInputs = with python3.pkgs; [
    unittestCheckHook
    httpx
  ];

  pythonImportsCheck = [ "whisper_api" ];

  meta = with lib; {
    description = "A simple API for OpenAI's Whisper";
    homepage = "https://github.com/MayNiklas/whisper_api";
    maintainers = with maintainers; [ MayNiklas ];
  };

}
