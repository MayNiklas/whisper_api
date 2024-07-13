{ pkgs, ... }:
let
  python-with-packages = pkgs.python3.withPackages (p: with p;   [
    fastapi
    ffmpeg-python
    openai-whisper
    python-multipart
    uvicorn
  ] ++ [
    # only needed for development
    autopep8
    httpx
    pytest
  ]);
in
pkgs.mkShell {
  buildInputs = with pkgs;[
    # only needed for development
    nixpkgs-fmt
    pre-commit

    python-with-packages
  ];
  shellHook = ''
    if [[ -z $using_direnv ]]; then
      # print information about the development shell
      echo "---------------------------------------------------------------------"
      echo "How to use this Nix development shell:"
      echo "python interpreter: ${python-with-packages}/bin/python3"
      echo "python site packages: ${python-with-packages}/${python-with-packages.sitePackages}"
      echo "---------------------------------------------------------------------"
      echo "In case you need to set the PYTHONPATH environment variable, run:"
      echo "export PYTHONPATH=${python-with-packages}/${python-with-packages.sitePackages}"
      echo "---------------------------------------------------------------------"
      echo "VSCode:"
      echo "1. Install the 'ms-python.python' extension"
      echo "2. Set the python interpreter to ${python-with-packages}/bin/python3"
      echo "---------------------------------------------------------------------"
      echo "PyCharm:"
      echo "TODO - please contribute!"
      echo "---------------------------------------------------------------------"
      echo "Running the whisper_api development server:"
      echo "cd src && uvicorn whisper_api:app --reload --host 127.0.0.1 --port 3001"
      echo "---------------------------------------------------------------------"
    fi
  '';
}
