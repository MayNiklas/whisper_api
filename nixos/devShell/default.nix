{ pkgs
, cudaSupport ? false
, ...
}:
let
  python-with-packages = pkgs.python3.withPackages (p: with p; [
    fastapi
    ffmpeg-python
    multipart
    (openai-whisper.override { torch = torch.override { inherit cudaSupport; openai-triton = openai-triton.override { inherit cudaSupport; }; }; })
    uvicorn

    # we want to evaluate faster-whisper against openai-whisper
    (faster-whisper.override {
      ctranslate2 = (ctranslate2.override {
        ctranslate2-cpp = (pkgs.ctranslate2.override {
          stdenv = if cudaSupport then pkgs.gcc11Stdenv else pkgs.stdenv;
          withCUDA = cudaSupport;
          withCuDNN = cudaSupport;
        });
      });
    })
  ] ++ [
    # only needed for development
    autopep8
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
