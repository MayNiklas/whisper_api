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
        };
      in
      rec {

        # Use nixpkgs-fmt for `nix fmt'
        formatter = pkgs.nixpkgs-fmt;

        devShells = {

          # nix develop
          default =
            let
              pkgs = import nixpkgs {
                inherit system;
                config = {
                  allowUnfree = true;
                  cudaSupport = true;
                };
              };
            in
            import ./shell.nix { inherit pkgs; };

          # nix develop .#withoutCUDA
          withoutCUDA =
            let
              pkgs = import nixpkgs {
                inherit system;
                config = {
                  allowUnfree = false;
                  cudaSupport = false;
                };
              };
            in
            import ./shell.nix { inherit pkgs; };

        };

        defaultPackage = packages.whisper_api;

        packages = flake-utils.lib.flattenTree rec {

          whisper_api = pkgs.python3Packages.callPackage ./default.nix { };

          whisper_api_withCUDA =
            let
              pkgs = import nixpkgs {
                inherit system;
                config = {
                  allowUnfree = true;
                  cudaSupport = true;
                };
              };
            in
            pkgs.python3Packages.callPackage ./default.nix { };

          whisper_api_withoutCUDA =
            let
              pkgs = import nixpkgs {
                inherit system;
                config = {
                  allowUnfree = false;
                  cudaSupport = false;
                };
              };
            in
            pkgs.python3Packages.callPackage ./default.nix { };

          whisper_cli = pkgs.python3Packages.buildPythonPackage rec {
            pname = "whisper_cli";
            # get version from version.py
            version = (pkgs.lib.strings.removePrefix ''__version__ = "''
              (pkgs.lib.strings.removeSuffix ''
                "
              ''
                (builtins.readFile ./whisper_api/version.py)));
            src = ./.;
            propagatedBuildInputs = with pkgs.python3Packages; [
              requests
            ];
            preBuild = ''
              rm requirements.txt
              touch requirements.txt
            '';
            doCheck = false;
            meta = with pkgs.lib; {
              description = "A simple API for OpenAI's Whisper";
              homepage = "https://github.com/MayNiklas/whisper_api";
              maintainers = with maintainers; [ MayNiklas ];
            };
          };

        };
      });
}
