# nix develop
# -> with CUDA support (only works on NixOS)
#
# nix develop .#withoutCUDA
# -> without CUDA support

{ pkgs ? import
    (
      let
        lock = builtins.fromJSON (builtins.readFile ./flake.lock);
      in
      builtins.fetchGit {
        name = "whisper-revision";
        url = "https://github.com/NixOS/nixpkgs/";
        ref = "refs/heads/nixos-unstable";
        rev = "${lock.nodes.nixpkgs.locked.rev}";
      }
    )
    { config = { allowUnfree = true; cudaSupport = true; }; }
}:
let
  python-with-packages = pkgs.python3.withPackages
    (p: with p; [
      fastapi
      multipart
      openai-whisper
      torch
      uvicorn
      # # https://github.com/elarivie/pyReaderWriterLock
      # (buildPythonPackage rec {
      #   pname = "pyReaderWriterLock";
      #   version = "1.0.9";
      #   src = pkgs.fetchFromGitHub {
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
    ] ++
    # only needed for development
    [
      autopep8
      pytest
    ]);
in
pkgs.mkShell
{

  buildInputs = with pkgs;[
    # only needed for development
    nixpkgs-fmt
    pre-commit

    # also in final package
    python-with-packages
  ];

  shellHook = ''
    export PYTHONPATH=${python-with-packages}/${python-with-packages.sitePackages}
    echo ${python-with-packages}
    echo "PYTHONPATH=$PYTHONPATH"

    # cd src
    # uvicorn whisper_api:app --reload --host 127.0.0.1 --port 3001
    # exit 0
  '';

}
