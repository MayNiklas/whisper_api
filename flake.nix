{

  description = "A simple API for OpenAI's Whisper";

  inputs = { nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable"; };

  outputs = { self, nixpkgs, ... }:
    let
      # System types to support.
      supportedSystems =
        [ "aarch64-darwin" "aarch64-linux" "x86_64-darwin" "x86_64-linux" ];
      cudaSystems = [ "x86_64-linux" ];

      # Helper function to generate an attrset '{ x86_64-linux = f "x86_64-linux"; ... }'.
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
      forCudaSystems = nixpkgs.lib.genAttrs cudaSystems;

      # Nixpkgs instantiated for supported system types.
      nixpkgsFor = forAllSystems (system:
        import nixpkgs {
          inherit system;
          overlays = [ self.overlays.default ];
        });

      # Nixpkgs instantiated for supported system types.
      # Including CUDA support (and consequently, proprietary drivers).
      nixpkgsForCUDA = forAllSystems (system:
        import nixpkgs {
          inherit system;
          overlays = [ self.overlays.default ];
          config = {
            allowUnfree = true;
            cudaSupport = true;
          };
        });

      # Nixpkgs instantiated for supported system types.
      # Explicitly without CUDA support (and consequently, proprietary drivers).
      nixpkgsForWithoutCUDA = forAllSystems (system:
        import nixpkgs {
          inherit system;
          overlays = [ self.overlays.default ];
          config = {
            allowUnfree = false;
            cudaSupport = false;
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
            , ffmpeg-python
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
              src = self;
              propagatedBuildInputs = [
                fastapi
                ffmpeg-python
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
        forCudaSystems
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
                  ffmpeg-python
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
        forCudaSystems
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

            authorizedMails = mkOption {
              type = types.str;
              default = "None";
              description = ''
                Users with these mails are authorized to request logs via the API.
                This is mainly used for debugging purposes.
                Multiple mails can be separated by a space.
              '';
            };

            dataDir = mkOption {
              type = types.str;
              default = "/var/lib/whisper_api";
              description = ''
                The directory where whisper_api stores its data files.
              '';
            };

            environment = mkOption {
              type = types.attrs;
              default = { };
              description = ''
                Environment variables to be passed to the whisper_api service.
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
                LOG_AUTHORIZED_MAILS = mkIf (cfg.authorizedMails != "None") cfg.authorizedMails;
              } // cfg.environment;
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
