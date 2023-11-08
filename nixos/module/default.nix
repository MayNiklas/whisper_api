{ lib, pkgs, config, ... }:
with lib;
let cfg = config.services.whisper_api; in
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
      default =
        if cfg.withCUDA then
          pkgs.whisper_api.override { cudaSupport = true; }
        else
          pkgs.whisper_api;
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

}
