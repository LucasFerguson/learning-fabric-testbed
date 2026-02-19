#!/usr/bin/env bash
set -euo pipefail

CFG_DIR="$HOME/code2025/learning-fabric-testbed/fabric_config"
RC_FILE="${CFG_DIR}/fabric_rc"

mkdir -p "$CFG_DIR"

# Required; set these before running, or edit here
: "${FABRIC_PROJECT_ID:=Pe34dd6bb-f899-499d-a7af-8dfa60559ecb}"
: "${FABRIC_BASTION_USERNAME:=lferguson_0000287022}"
: "${FABRIC_TOKEN_LOCATION:=${CFG_DIR}/token.json}"

cat > "$RC_FILE" <<EOF
# Source this file before running FABlib scripts:
#   source ~/work/fabric_config/fabric_rc
#
# Common failures:
# - token path wrong, or token is expired
# - project id wrong, or you are not in that project
# - key permissions too open; private keys should be chmod 600

export FABRIC_CREDMGR_HOST=cm.fabric-testbed.net
export FABRIC_ORCHESTRATOR_HOST=orchestrator.fabric-testbed.net
export FABRIC_BASTION_HOST=bastion.fabric-testbed.net

export FABRIC_PROJECT_ID=${FABRIC_PROJECT_ID}
export FABRIC_TOKEN_LOCATION=${FABRIC_TOKEN_LOCATION}

export FABRIC_BASTION_USERNAME=${FABRIC_BASTION_USERNAME}
export FABRIC_BASTION_KEY_LOCATION=${CFG_DIR}/fabric_bastion_key

export FABRIC_SLICE_PRIVATE_KEY_FILE=${CFG_DIR}/slice_key
export FABRIC_SLICE_PUBLIC_KEY_FILE=${CFG_DIR}/slice_key.pub

# Optional if your keys are encrypted
# export FABRIC_BASTION_KEY_PASSPHRASE=...
# export FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE=...
EOF

chmod 600 "$RC_FILE"
echo "[+] Wrote $RC_FILE"
