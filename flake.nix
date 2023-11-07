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

      overlays.default = final: prev: {
        whisper_api = with final;  pkgs.python3Packages.callPackage nixos/pkgs/whisper_api { };
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
                  # we need to evaluate faster-whisper
                  faster-whisper
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
        in
        {

          options.services.whisper_api = {

            enable = mkEnableOption "whisper_api";

            withCUDA = mkOption {
              type = types.bool;
              default = false;
              description = ''
                Whether to use CUDA.
                Mutually exclusive with `package`.
              '';
            };

            package = mkOption {
              type = types.package;
              default = if cfg.withCUDA then self.packages.${pkgs.system}.whisper_api_withCUDA else self.packages.${pkgs.system}.whisper_api_withoutCUDA;
              description = ''
                The whisper_api package to use.
              '';
            };

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
              type = types.listOf types.str;
              default = [ ];
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
                LOG_AUTHORIZED_MAILS = mkIf (cfg.authorizedMails != [ ]) (lib.strings.concatStringsSep " " cfg.authorizedMails);
              } // cfg.environment;
              serviceConfig = mkMerge [
                {
                  User = cfg.user;
                  Group = cfg.group;
                  WorkingDirectory = cfg.dataDir;
                  ExecStart = "${cfg.package}/bin/whisper_api";
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

      # nix run .\#checks.vmTest.driver
      checks = let system = "x86_64-linux"; in {
        vmTest = with import (nixpkgs + "/nixos/lib/testing-python.nix") { inherit system; };
          makeTest {
            name = "whisper-service-test";
            nodes = {

              client = { pkgs, ... }: {
                imports = [ ];
                networking = {
                  dhcpcd.enable = false;
                  interfaces.eth1.ipv4.addresses = [{
                    address = "192.168.0.2";
                    prefixLength = 24;
                  }];
                };
              };

              server = { pkgs, ... }: {
                imports = [ self.nixosModules.whisper_api ];
                services.whisper_api = {
                  enable = true;
                  package = self.packages.${system}.whisper_api_withoutCUDA;
                  maxModel = "base";
                  listen = "0.0.0.0";
                  port = 3001;
                  openFirewall = true;
                  environment = { };
                };
                networking = {
                  dhcpcd.enable = false;
                  useNetworkd = true;
                  useDHCP = false;
                  interfaces.eth1.ipv4.addresses = [{
                    address = "192.168.0.1";
                    prefixLength = 24;
                  }];
                };
              };

            };
            testScript =
              let
                base_model = (pkgs.fetchurl {
                  url = "https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt";
                  hash = "sha256-7ToLaxwO34ea2bEbGvWg5qtduSBfiR9mj4sObGMm404=";
                });
                test_file = (pkgs.fetchurl {
                  url = "https://upload.wikimedia.org/wikipedia/commons/6/6d/En-Open_Source_Software_CD-article.ogg";
                  hash = "sha256-rmgqP2cXZO0e/GAvLUYAaOa44kIiyooxwGQI/FbJuW4=";
                });
                python_for_test = pkgs.python3.withPackages (p: with p;  [ requests ]);
                test_python = (pkgs.writeTextFile {
                  name = "test.py";
                  text = ''
                    import time
                    import requests
                    import logging

                    logger = logging.getLogger('logger')
                    logger.setLevel(logging.DEBUG)

                    url = 'http://192.168.0.1:3001/api/v1/'

                    while (reply := requests.get(url + 'decoder_status').json()['is_model_loaded']) != True:
                        logger.info("Waiting for model to load...")
                        time.sleep(1)

                    time.sleep(3)

                    # post audio file)
                    files = {'file': open('${test_file}', 'rb')}
                    r = requests.post(url + 'transcribe', files=files).json()

                    # get transcript
                    while (reply := requests.get(url + 'status?task_id=' + r['task_id']).json())['status'] != 'finished':
                        logger.info("Waiting for the transcript...")
                        time.sleep(1)

                    logger.info(reply['transcript'])
                  '';
                });
              in
              ''
                start_all()

                # copy the model to /var/lib/whisper_api/.cache/whisper/tiny.pt on the server
                server.succeed("mkdir -p /var/lib/whisper_api/.cache/whisper")
                server.succeed("cp ${base_model} /var/lib/whisper_api/.cache/whisper/base.pt")
                server.succeed("chown -R whisper_api:whisper_api /var/lib/whisper_api/.cache/whisper")

                # wait until the client is up
                client.wait_for_unit("network-online.target")

                # wait until the server is up
                server.wait_for_unit("network-online.target")
                server.wait_for_unit("whisper_api")

                # check if client can reach server
                client.wait_until_succeeds("ping -c 1 192.168.0.1")

                # check if server can reach API
                server.wait_until_succeeds("${pkgs.curl}/bin/curl http://127.0.0.1:3001/api/v1/decoder_status")
                server.wait_until_succeeds("${pkgs.curl}/bin/curl http://192.168.0.1:3001/api/v1/decoder_status")

                # check if client can reach API
                client.wait_until_succeeds("${pkgs.curl}/bin/curl http://192.168.0.1:3001/api/v1/decoder_status")

                # actually test the API
                client.succeed("${python_for_test}/bin/python3 ${test_python}")
              '';
          };
      };

    };
}
