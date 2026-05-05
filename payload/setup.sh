#!/usr/bin/env bash
# setup.sh — uploaded and run on a FABRIC slice node by create_slice.py
# Logs everything to ~/setup.log, then clones the htcondor repo.

LOGFILE="$HOME/setup.log"
REPO_URL="https://github.com/LucasFerguson/learning-htcondor-ospool.git"
CLONE_DIR="$HOME/learning-htcondor-ospool"

log() {
    local ts
    ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "[$ts] $*" | tee -a "$LOGFILE"
}

log "================================================================"
log "=== setup.sh started ==="
log "================================================================"

# ── Step 0: basic system info ────────────────────────────────────────
log ""
log "--- Step 0: system info ---"
log "Hostname    : $(hostname)"
log "User        : $(whoami)"
log "Working dir : $(pwd)"
log "Kernel      : $(uname -r)"

if [ -f /etc/os-release ]; then
    OS=$(grep PRETTY_NAME /etc/os-release | cut -d= -f2 | tr -d '"')
    log "OS          : $OS"
else
    log "OS          : /etc/os-release not found"
fi

log "Uptime      : $(uptime -p 2>/dev/null || uptime)"
log "Disk (/)    : $(df -h / | awk 'NR==2 {print $3 " used / " $2 " total (" $5 " full)"}')"
log "Memory      : $(free -h | awk '/^Mem:/ {print $3 " used / " $2 " total"}')"
log "CPU cores   : $(nproc)"

# ── Step 1: network reachability ────────────────────────────────────
log ""
log "--- Step 1: network reachability ---"

check_host() {
    local label="$1" host="$2"
    if ping -c 2 -W 4 "$host" &>/dev/null; then
        log "  [OK]   ping $label ($host)"
    else
        log "  [FAIL] ping $label ($host) — no response"
    fi
}

check_host "internet (8.8.8.8)"   "8.8.8.8"
check_host "GitHub DNS"           "github.com"

# check that payload/learning-htcondor-ospool folder is there and has expected files
log ""
log "--- Listing current directory contents ---"
ls -la | while IFS= read -r line; do
    log "  $line"
done

log ""
log "--- Listing payload/ directory contents ---"
if [ -d "payload" ]; then
    ls -la payload/ | while IFS= read -r line; do
        log "  $line"
    done
else
    log "  [WARN] payload/ directory not found"
fi

# ── Step 1.5: navigate to learning-htcondor-ospool and run OSPool workflow ───
log ""
log "--- Running OSPool workflow script ---"
HTCONDOR_DIR="$HOME/payload/learning-htcondor-ospool"

if [ -d "$HTCONDOR_DIR" ]; then
    log "  Found $HTCONDOR_DIR"
    log "  Contents of $HTCONDOR_DIR:"
    ls -la "$HTCONDOR_DIR" | while IFS= read -r line; do
        log "    $line"
    done

    # Pre-populate known_hosts so SSH doesn't prompt during workflow
    mkdir -p ~/.ssh && chmod 700 ~/.ssh
    ssh-keyscan -H ap40.uw.osg-htc.org >> ~/.ssh/known_hosts 2>/dev/null
    log "  [OK]   Added ap40.uw.osg-htc.org to known_hosts"

    # Fix SSH key permissions (required by SSH — must not be world/group readable)
    if [ -f "$HTCONDOR_DIR/sshkey/ospool_ed25519" ]; then
        chmod 600 "$HTCONDOR_DIR/sshkey/ospool_ed25519"
        log "  [OK]   Set permissions 600 on sshkey/ospool_ed25519"
    fi

    # Look for workflow script
    if [ -f "$HTCONDOR_DIR/run_ospool_workflow.sh" ]; then
        log "  [INFO] Running run_ospool_workflow.sh"
        cd "$HTCONDOR_DIR" || exit 1
        if bash run_ospool_workflow.sh >> "$LOGFILE" 2>&1; then
            log "  [OK]   run_ospool_workflow.sh completed successfully"
        else
            log "  [WARN] run_ospool_workflow.sh returned non-zero exit code"
        fi
        cd - > /dev/null || exit 1
    else
        log "  [WARN] run_ospool_workflow.sh not found in $HTCONDOR_DIR"
    fi
else
    log "  [WARN] $HTCONDOR_DIR not found — expected at $HTCONDOR_DIR"
fi

# ── Step 2: check / install git ─────────────────────────────────────
# log ""
# log "--- Step 2: git availability ---"

# if command -v git &>/dev/null; then
#     log "  [OK]   git already installed: $(git --version)"
# else
#     log "  [INFO] git not found — attempting apt install"
#     log "  Running: sudo apt-get update -qq"
#     if sudo apt-get update -qq >> "$LOGFILE" 2>&1; then
#         log "  apt-get update succeeded"
#     else
#         log "  [WARN] apt-get update returned non-zero; continuing anyway"
#     fi

#     log "  Running: sudo apt-get install -y git"
#     if sudo apt-get install -y git >> "$LOGFILE" 2>&1; then
#         log "  [OK]   git installed: $(git --version)"
#     else
#         log "  [FAIL] apt-get install git failed — cannot proceed with clone"
#         log "  setup.sh exiting with error"
#         exit 1
#     fi
# fi

# ── Step 3: clone repo ───────────────────────────────────────────────
# log ""
# log "--- Step 3: clone $REPO_URL ---"
# log "  Target dir: $CLONE_DIR"

# if [ -d "$CLONE_DIR/.git" ]; then
#     log "  [SKIP]  repo already cloned at $CLONE_DIR"
#     log "  Running: git -C $CLONE_DIR log --oneline -5"
#     git -C "$CLONE_DIR" log --oneline -5 2>&1 | while IFS= read -r line; do
#         log "    $line"
#     done
# else
#     log "  Running: git clone $REPO_URL $CLONE_DIR"
#     if git clone "$REPO_URL" "$CLONE_DIR" >> "$LOGFILE" 2>&1; then
#         log "  [OK]   clone succeeded"
#         log "  Top-level contents:"
#         ls "$CLONE_DIR" 2>&1 | while IFS= read -r line; do
#             log "    $line"
#         done
#         log "  Recent commits:"
#         git -C "$CLONE_DIR" log --oneline -5 2>&1 | while IFS= read -r line; do
#             log "    $line"
#         done
#     else
#         log "  [FAIL] git clone returned non-zero — check log above for git output"
#         log "  Possible causes: no network, DNS failure, repo is private, git not configured"
#         exit 1
#     fi
# fi

# ── Done ─────────────────────────────────────────────────────────────
log ""
log "================================================================"
log "=== setup.sh finished successfully ==="
log "================================================================"
log "Full log written to: $LOGFILE"
