#!/usr/bin/env bash
set -euo pipefail

WIN_SSH_DIR="/mnt/c/Users/lucas/.ssh"
CFG_DIR="$HOME/code2025/learning-fabric-testbed/fabric_config"

mkdir -p "$CFG_DIR"

# Change these if your filenames differ
WIN_BASTION_KEY="${WIN_SSH_DIR}/id_rsa"
WIN_SLICE_KEY="${WIN_SSH_DIR}/slice_key_2025-11-19"

WSL_BASTION_KEY="${CFG_DIR}/fabric_bastion_key"
WSL_SLICE_KEY="${CFG_DIR}/slice_key"

echo "[*] Copying keys into WSL config dir: ${CFG_DIR}"

if [[ ! -f "$WIN_BASTION_KEY" ]]; then
  echo "[!] Missing Windows bastion key: $WIN_BASTION_KEY"
  echo "    Fix the path or choose a different key."
  exit 2
fi

if [[ ! -f "$WIN_SLICE_KEY" ]]; then
  echo "[!] Missing Windows slice key: $WIN_SLICE_KEY"
  echo "    Fix the path or choose a different key."
  exit 2
fi

# Copy private keys
cp -f "$WIN_BASTION_KEY" "$WSL_BASTION_KEY"
cp -f "$WIN_SLICE_KEY" "$WSL_SLICE_KEY"

# Copy public key for slice; if you do not have it, generate it from the private key
if [[ -f "${WIN_SLICE_KEY}.pub" ]]; then
  cp -f "${WIN_SLICE_KEY}.pub" "${WSL_SLICE_KEY}.pub"
else
  echo "[*] slice public key not found; generating ${WSL_SLICE_KEY}.pub"
  ssh-keygen -y -f "$WSL_SLICE_KEY" > "${WSL_SLICE_KEY}.pub"
fi

# Permissions; common failure cause if too open
chmod 700 "$HOME"
chmod 700 "$HOME/fabric_config" || true
chmod 700 "$CFG_DIR"
chmod 600 "$WSL_BASTION_KEY" "$WSL_SLICE_KEY"
chmod 644 "${WSL_SLICE_KEY}.pub"

echo "[+] Done."
echo "    Bastion key: $WSL_BASTION_KEY"
echo "    Slice key:   $WSL_SLICE_KEY"
