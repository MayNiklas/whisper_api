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
  '';

}
