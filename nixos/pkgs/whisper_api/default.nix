{ self
, lib
, python3
,
}:
python3.pkgs.buildPythonApplication {

  pname = "whisper_api";

  # get version by reading __version__ from src/whisper_api/version.py
  version = lib.strings.removeSuffix ''"''
    (lib.strings.removePrefix ''__version__ = "'' (lib.elemAt
      (lib.filter (line: lib.hasPrefix "__version__" line) (lib.splitString "\n"
        (builtins.readFile "${self}/src/whisper_api/__init__.py"))) 0));

  pyproject = true;
  src = self;

  pythonRelaxDeps = [ ];

  nativeBuildInputs = with python3.pkgs; [
    setuptools
    pythonRelaxDepsHook
  ];

  propagatedBuildInputs = with python3.pkgs; [
    # temporary workaround for https://github.com/NixOS/nixpkgs/issues/335841
    (fastapi.overrideAttrs {
      postInstall = ''
        rm -r $out/bin
      '';
    })
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
