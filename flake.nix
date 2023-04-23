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
    {

      nixosModules.whisper_api = { lib, pkgs, config, ... }:
        with lib;
        let
          cfg = config.services.whisper_api;
          whisper_api = self.packages.${pkgs.system}.whisper_api_withCUDA;
        in
        {

          options.services.whisper_api = {

            enable = mkEnableOption "whisper_api";

            preload = mkOption {
              type = types.bool;
              default = false;
              description = ''
                Whether to preload the model.
              '';
            };

            dataDir = mkOption {
              type = types.str;
              default = "/var/lib/whisper_api";
              description = ''
                The directory where whisper_api stores its data files.
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

            envfile = mkOption {
              type = types.str;
              default = "/var/src/secrets/whisper_api/envfile";
              description = ''
                The location of the envfile containing secrets
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
              environment = {
                PRELOAD = mkIf cfg.preload "true";
                LISTEN = cfg.listen;
                PORT = "${toString cfg.port}";
              };
              serviceConfig = mkMerge [
                {
                  # EnvironmentFile = [ cfg.envfile ];
                  User = cfg.user;
                  Group = cfg.group;
                  WorkingDirectory = "${whisper_api.src}";
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
    }

    //

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
            version = (pkgs.lib.strings.removePrefix '' __version__ = "''
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
