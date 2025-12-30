{ pkgs, ... }: {
  channel = "stable-23.11";
  packages = [
    pkgs.python3
    pkgs.gcc
  ];
  env = {};
}
