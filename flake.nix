{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  # only used for `nix develop'
  nixConfig = {
    extra-trusted-public-keys = "cache.lounge.rocks:uXa8UuAEQoKFtU8Om/hq6d7U+HgcrduTVr8Cfl6JuaY=";
    extra-substituters = "https://cache.lounge.rocks?priority=100";
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config = {
            allowUnfree = true;
            cudaSupport = true;
          };
        };
        python = pkgs.python310;
        python-packages = with python.pkgs; [
          fastapi
          multipart
          openai-whisper
          torch
          uvicorn
        ];
      in
      rec {

        # Use nixpkgs-fmt for `nix fmt'
        formatter = pkgs.nixpkgs-fmt;

        # nix develop
        devShells.default =
          let
            python-with-packages = python.withPackages (ps: python-packages);
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
            };

        defaultPackage = packages.whisper_api;
        packages = flake-utils.lib.flattenTree rec {

          whisper_api = with python.pkgs;
            buildPythonPackage rec {
              pname = "whisper_api";
              version = (lib.strings.removePrefix ''__version__ = "''
                (lib.strings.removeSuffix ''
                  "
                ''
                  (builtins.readFile ./whisper_api/version.py)));
              src = self;
              propagatedBuildInputs = python-packages;
              doCheck = false;
            };

        };
      });
}
