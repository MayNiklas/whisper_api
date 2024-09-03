let
  flake = (import
    (
      let
        lock = builtins.fromJSON (builtins.readFile ./flake.lock);
      in
      fetchTarball {
        url = "https://github.com/edolstra/flake-compat/archive/${lock.nodes.flake-compat.locked.rev}.tar.gz";
        sha256 = lock.nodes.flake-compat.locked.narHash;
      }
    )
    {
      src = ./.;
    });
in
{
  whisper_api = (flake.defaultNix.outputs.packages.${builtins.currentSystem}.whisper_api);
  whisper_api_withCUDA = (flake.defaultNix.outputs.packages.${builtins.currentSystem}.whisper_api_withCUDA);
  whisper_api_withoutCUDA = (flake.defaultNix.outputs.packages.${builtins.currentSystem}.whisper_api_withoutCUDA);
}
