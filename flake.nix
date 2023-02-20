{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
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
      in
      rec {

        # Use nixpkgs-fmt for `nix fmt'
        formatter = pkgs.nixpkgs-fmt;

        defaultPackage = packages.whisper_api;

        packages = flake-utils.lib.flattenTree rec {

          whisper_api = with pkgs.python310Packages;
            buildPythonPackage rec {
              pname = "whisper_api";
              version = "20230220";
              src = self;
              propagatedBuildInputs = [
                fastapi
                multipart
                openai-whisper
                torch
                uvicorn
              ];
              doCheck = false;
            };

        };
      });
}
