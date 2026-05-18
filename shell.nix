with import <nixpkgs> { };
pkgs.mkShell {
  name = "lab28"; # change this to something more catchy

  # Here is where you will add all the libraries required by your native modules
  # You can use the following one-liner to find out which ones you need.
  # Just make sure you have `gcc` installed.
  # `find .venv/ -type f -name "*.so" | xargs ldd | grep "not found" | sort | uniq`
  NIX_LD_LIBRARY_PATH = lib.makeLibraryPath [
    stdenv.cc.cc # libstdc++
    zlib # libz (for numpy)
  ];

  NIX_LD = lib.fileContents "${stdenv.cc}/nix-support/dynamic-linker";

  # --- SSL Certificate Fixes ---
  SSL_CERT_FILE = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
  GIT_SSL_CAINFO = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
  REQUESTS_CA_BUNDLE = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";

  packages = with pkgs; [
    # If you're using Poetry, comment out `uv` and uncomment the following two lines:
    #   python313 # set to your Python version
    #   poetry
    uv
    basedpyright
    ruff
    black

    # --- Added for building pyarrow (Option 2) ---
    cmake
    gcc
    gnumake
    # ---------------------------------------------
  ];

  shellHook = ''
    # Keep the library path for Python and Next.js SWC binaries
    export LD_LIBRARY_PATH=$NIX_LD_LIBRARY_PATH
  '';
}
