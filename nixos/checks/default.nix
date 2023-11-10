{ nixpkgs, modules, ... }:
let system = "x86_64-linux";
in {
  ${system}.vmTest = with import (nixpkgs + "/nixos/lib/testing-python.nix") { inherit system; };
    makeTest {
      name = "whisper-service-test";
      nodes = {

        server = { pkgs, ... }: {
          imports = with modules; [ whisper_api ];
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
            interfaces.eth0.ipv4.addresses = [{
              address = "192.168.0.1";
              prefixLength = 24;
            }];
          };
        };

      };

      testScript =
        let
          base_model = (pkgs.fetchurl {
            url =
              "https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt";
            hash = "sha256-7ToLaxwO34ea2bEbGvWg5qtduSBfiR9mj4sObGMm404=";
          });
          test_file = (pkgs.fetchurl {
            url =
              "https://upload.wikimedia.org/wikipedia/commons/6/6d/En-Open_Source_Software_CD-article.ogg";
            hash = "sha256-rmgqP2cXZO0e/GAvLUYAaOa44kIiyooxwGQI/FbJuW4=";
          });
          python_for_test = pkgs.python3.withPackages (p: with p; [ requests ]);
          test_python = (pkgs.writeTextFile {
            name = "test.py";
            text = ''
              import time
              import requests
              import logging

              logger = logging.getLogger('logger')
              logger.setLevel(logging.DEBUG)

              url = 'http://127.0.0.1:3001/api/v1/'

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

          # wait until the server is up
          server.wait_for_unit("network-online.target")
          server.wait_for_unit("whisper_api")

          # check if server can reach API
          server.wait_until_succeeds("${pkgs.curl}/bin/curl http://127.0.0.1:3001/api/v1/decoder_status")

          # actually test the API
          server.succeed("${python_for_test}/bin/python3 ${test_python}")
        '';
    };
}
