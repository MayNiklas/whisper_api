{

  description = "A simple API for OpenAI's Whisper";

  inputs = { nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable"; };

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

      # Nixpkgs instantiated for x86_64-linux.
      # Including CUDA support (and consequently, proprietary drivers).
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
        devShell = with final; pkgs.callPackage nixos/devShell { };
        whisper_api = with final; pkgs.python3Packages.callPackage nixos/pkgs/whisper_api { inherit self; };
      };

      packages = forAllSystems (system:
        let pkgs = nixpkgsFor.${system}; in {
          default = pkgs.whisper_api;
          whisper_api = pkgs.whisper_api;
          whisper_api_withoutCUDA = pkgs.whisper_api;
        } // pkgs.lib.optionalAttrs (system == "x86_64-linux") {
          whisper_api_withCUDA = pkgs.whisper_api.override { cudaSupport = true; };
        }
      );

      devShells = forAllSystems (system:
        let pkgs = nixpkgsFor.${system}; in {
          default = pkgs.devShell;
          withoutCUDA = pkgs.devShell;
        } // pkgs.lib.optionalAttrs (system == "x86_64-linux") {
          # TODO: currently we use nixpkgsCUDA for devShell
          # not all dependencies have a cudaSupport option.        
          withCUDA = nixpkgsCUDA.devShell;
        }
      );

      nixosModules = {
        whisper_api = {
          imports = [ ./nixos/module ];
          nixpkgs.overlays = [ self.overlays.default ];
        };
      };

      # nix run .\#checks.x86_64-linux.vmTest.driver
      checks = let system = "x86_64-linux"; in {
        ${system} = {
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

    };
}
