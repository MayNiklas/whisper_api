{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs, ... }:
    let
      # System types to support.
      supportedSystems = [ "aarch64-darwin" "aarch64-linux" "x86_64-darwin" "x86_64-linux" ];
      linuxSystems = [ "aarch64-linux" "x86_64-linux" ];

      # Helper function to generate an attrset '{ x86_64-linux = f "x86_64-linux"; ... }'.
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
      forLinuxSystems = nixpkgs.lib.genAttrs linuxSystems;

      # Nixpkgs instantiated for supported system types.
      nixpkgsFor = forAllSystems (system:
        import nixpkgs {
          inherit system;
          overlays = [ self.overlays.default ];
        });

      nixpkgsForCUDA = forAllSystems (system:
        import nixpkgs {
          inherit system;
          overlays = [ self.overlays.default ];
          config = {
            allowUnfree = true;
            cudaSupport = true;
          };
        });

      nixpkgsForWithoutCUDA = forAllSystems (system:
        import nixpkgs {
          inherit system;
          overlays = [ self.overlays.default ];
          config = {
            allowUnfree = true;
            cudaSupport = true;
          };
        });
    in
    {

      # `nix fmt`
      formatter = forAllSystems
        (system: nixpkgsFor.${system}.nixpkgs-fmt);

      overlays.default =
        let
          package =
            { lib
            , buildPythonPackage
              # propagates
            , torch
            , fastapi
            , multipart
            , openai-whisper
            , uvicorn
              # tests
            , pytestCheckHook
            }:
            buildPythonPackage {
              pname = "whisper_api";
              version = (lib.strings.removePrefix ''__version__ = "''
                (lib.strings.removeSuffix ''
                  "
                ''
                  (builtins.readFile ./src/whisper_api/version.py)));
              format = "setuptools";
              src = ./.;
              propagatedBuildInputs = [
                fastapi
                multipart
                openai-whisper
                torch
                uvicorn
              ];
              nativeCheckInputs = [ pytestCheckHook ];
              pythonImportsCheck = [ "whisper_api" ];
              meta = with lib; {
                description = "A simple API for OpenAI's Whisper";
                homepage = "https://github.com/MayNiklas/whisper_api";
                maintainers = with maintainers; [ MayNiklas ];
              };
            };
        in
        final: prev: {
          whisper_api = with final;  pkgs.python3Packages.callPackage package { };
        };

      # Packages
      packages =
        forAllSystems
          (system: {
            default = self.packages.${system}.whisper_api;
            whisper_api = nixpkgsFor.${system}.whisper_api;
            whisper_api_withoutCUDA = nixpkgsForWithoutCUDA.${system}.whisper_api;
          })
        //
        forLinuxSystems
          (system: {
            default = self.packages.${system}.whisper_api;
            whisper_api = nixpkgsFor.${system}.whisper_api;
            whisper_api_withCUDA = nixpkgsForCUDA.${system}.whisper_api;
            whisper_api_withoutCUDA = nixpkgsForWithoutCUDA.${system}.whisper_api;
          });

      devShells =
        let
          whisper-shell = { pkgs, ... }:
            let
              python-with-packages = pkgs.python3.withPackages (p: with p;
                [
                  fastapi
                  multipart
                  openai-whisper
                  torch
                  uvicorn
                ] ++
                # only needed for development
                [ autopep8 pytest ]);
            in
            pkgs.mkShell {
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
            };
        in
        forAllSystems
          (system: {
            # nix develop
            default = whisper-shell { pkgs = nixpkgsFor.${system}; };
            # nix develop .#withoutCUDA
            withoutCUDA = whisper-shell { pkgs = nixpkgsForWithoutCUDA.${system}; };
          })
        //
        forLinuxSystems
          (system: {
            # nix develop
            default = whisper-shell { pkgs = nixpkgsFor.${system}; };
            # nix develop .#withCUDA
            withCUDA = whisper-shell { pkgs = nixpkgsForCUDA.${system}; };
            # nix develop .#withoutCUDA
            withoutCUDA = whisper-shell { pkgs = nixpkgsForWithoutCUDA.${system}; };
          });

      nixosModules.whisper_api = { lib, pkgs, config, ... }:
        with lib;
        let
          cfg = config.services.whisper_api;
          # TODO:
          # a CUDA / non-CUDA version option would be nice
          whisper_api = self.packages.${pkgs.system}.whisper_api_withCUDA;
        in
        {

          options.services.whisper_api = {

            enable = mkEnableOption "whisper_api";

            listen = mkOption {
              type = types.str;
              default = "127.0.0.1";
              description = ''
                The address on which whisper_api listens.
              '';
            };

            port = mkOption {
              type = types.port;
              default = 3001;
              description = ''
                The port on which whisper_api listens.
              '';
            };

            openFirewall = mkOption {
              type = types.bool;
              default = false;
              description = lib.mdDoc ''
                Open the appropriate ports in the firewall for whisper_api.
              '';
            };

            loadModelOnStartup = mkOption {
              type = types.bool;
              default = true;
              description = ''
                Whether to load the model on startup.
              '';
            };

            unloadModelAfterSeconds = mkOption {
              type = types.int;
              default = 0;
              description = ''
                Unload the model after the specified number of seconds.
              '';
            };

            maxModel = mkOption {
              type = types.str;
              default = "None";
              description = ''
                The maximum model size.
                Choose between "tiny", "small", "medium" and "large"
              '';
            };

            dataDir = mkOption {
              type = types.str;
              default = "/var/lib/whisper_api";
              description = ''
                The directory where whisper_api stores its data files.
              '';
            };

            user = mkOption {
              type = types.str;
              default = "whisper_api";
              description = "User account under which whisper_api services run.";
            };

            group = mkOption {
              type = types.str;
              default = "whisper_api";
              description = "Group under which which whisper_api services run.";
            };

          };

          config = mkIf cfg.enable {

            systemd.services.whisper_api = {
              description = "A whisper API.";
              wantedBy = [ "multi-user.target" ];
              # TODO:
              # expose all environment variables as Nix options
              environment = {
                PORT = "${toString cfg.port}";
                LISTEN = cfg.listen;
                LOAD_MODEL_ON_STARTUP = mkIf (cfg.loadModelOnStartup == false) "0";
                MAX_MODEL = mkIf (cfg.maxModel != "None") cfg.maxModel;
                UNLOAD_MODEL_AFTER_S = mkIf (cfg.unloadModelAfterSeconds != 0) (toString cfg.unloadModelAfterSeconds);
              };
              serviceConfig = mkMerge [
                {
                  User = cfg.user;
                  Group = cfg.group;
                  # TODO:
                  # currently this causes a permission issue!
                  # we need to manually run
                  # `chown -R whisper_api:whisper_api /var/lib/whisper_api'
                  # after the home directory is created.
                  WorkingDirectory = cfg.dataDir;
                  ExecStart = "${whisper_api}/bin/whisper_api";
                  Restart = "on-failure";
                }
              ];
            };

            users.users = mkIf
              (cfg.user == "whisper_api")
              {
                whisper_api = {
                  isSystemUser = true;
                  createHome = true;
                  home = cfg.dataDir;
                  group = "whisper_api";
                  description = "whisper_api system user";
                };
              };

            users.groups = mkIf (cfg.group == "whisper_api") {
              whisper_api = { };
            };

            networking.firewall = mkIf (cfg.openFirewall && cfg.listen != "127.0.0.1") {
              allowedTCPPorts = [ cfg.port ];
            };

          };
          meta = { maintainers = with lib.maintainers; [ MayNiklas ]; };

        };

    };
}
