{

  description = "A simple API for OpenAI's Whisper";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-compat.url = "github:edolstra/flake-compat";
  };

  outputs = { self, nixpkgs, flake-compat, ... }:
    let
      # System types to support.
      supportedSystems = [ "aarch64-darwin" "aarch64-linux" "x86_64-darwin" "x86_64-linux" ];

      # Helper function to generate an attrset '{ x86_64-linux = f "x86_64-linux"; ... }'.
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;

      # Nixpkgs instantiated for supported system types.
      nixpkgsFor = forAllSystems (system:
        import nixpkgs {
          inherit system;
          overlays = [ self.overlays.default ];
          config = { allowUnfree = true; };
        });

      # Nixpkgs with CUDA support for x86_64-linux
      nixpkgsCUDA = import nixpkgs {
        system = "x86_64-linux";
        overlays = [ self.overlays.default ];
        config = { allowUnfree = true; cudaSupport = true; };
      };
    in
    {

      formatter = forAllSystems
        (system: nixpkgsFor.${system}.nixpkgs-fmt);

      overlays.default = final: prev: {
        devShell = final.callPackage nixos/devShell { inherit self; };
        whisper_api = final.callPackage nixos/pkgs/whisper_api { inherit self; };
        # Our code is not compatible with pydantic version 2 yet.
        python3 = prev.python3.override {
          packageOverrides = python-self: python-super: {
            # fastapi = python-super.fastapi.override { pydantic = python-super.pydantic_1; };
          };
        };
      };

      packages = forAllSystems (system:
        let pkgs = nixpkgsFor.${system}; in {
          default = pkgs.whisper_api;
          whisper_api = pkgs.whisper_api;
          whisper_api_withoutCUDA = pkgs.whisper_api;
        } // pkgs.lib.optionalAttrs (system == "x86_64-linux") {
          whisper_api_withCUDA = nixpkgsCUDA.whisper_api;
        }
      );

      devShells = forAllSystems (system:
        let pkgs = nixpkgsFor.${system}; in {
          default = pkgs.devShell;
          withoutCUDA = pkgs.devShell;
        } // pkgs.lib.optionalAttrs (system == "x86_64-linux") {
          withCUDA = nixpkgsCUDA.devShell;
        }
      );

      nixosModules = {
        whisper_api = {
          imports = [ ./nixos/module ];
          nixpkgs.overlays = [
            (final: prev:
              let system = prev.system; in
              {
                whisper_api = nixpkgsFor.${system}.python3Packages.callPackage nixos/pkgs/whisper_api { inherit self; };
                whisper_api_withCUDA = nixpkgsCUDA.python3Packages.callPackage nixos/pkgs/whisper_api { inherit self; };
              })
          ];
        };
      };

      # nix run .\#checks.x86_64-linux.vmTest.driver
      checks = import ./nixos/checks { nixpkgs = nixpkgs; modules = self.nixosModules; };

    };
}
