{

  description = "A simple API for OpenAI's Whisper";

  inputs = { nixpkgs.url = "github:mweinelt/nixpkgs/openai-whisper-20231117"; };

  outputs = { self, nixpkgs, ... }:
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

      nixpkgsCUDA = forAllSystems (system:
        import nixpkgs {
          inherit system;
          overlays = [ self.overlays.default ];
          config = { allowUnfree = true; cudaSupport = true; };
        });
    in
    {

      formatter = forAllSystems
        (system: nixpkgsFor.${system}.nixpkgs-fmt);

      overlays.default = final: prev: {
        devShell = with final; pkgs.callPackage nixos/devShell { };
        whisper_api = with final; pkgs.python3Packages.callPackage nixos/pkgs/whisper_api { inherit self; };
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
          # TODO: currently we use nixpkgsCUDA for devShell
          # not all dependencies have a cudaSupport option.        
          withCUDA = pkgs.devShell.override { cudaSupport = true; };
        }
      );

      nixosModules = {
        whisper_api = {
          imports = [ ./nixos/module ];
          nixpkgs.overlays = [ self.overlays.default ];
        };
      };

      # nix run .\#checks.x86_64-linux.vmTest.driver
      checks = import ./nixos/checks { nixpkgs = nixpkgs; modules = self.nixosModules; };

    };
}
