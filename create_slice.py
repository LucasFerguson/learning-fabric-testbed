#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from fabrictestbed_extensions.fablib.fablib import FablibManager

def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def _load_token_payload(token_path: Path) -> dict | None:
    if not token_path.exists():
        return None
    data = json.loads(token_path.read_text())
    token = data.get("id_token") or data.get("access_token") or data.get("token")
    if not token:
        return None
    parts = token.split(".")
    if len(parts) < 2:
        return None
    payload_b64 = parts[1]
    payload_b64 += "=" * (-len(payload_b64) % 4)
    payload = base64.urlsafe_b64decode(payload_b64.encode("utf-8"))
    return json.loads(payload.decode("utf-8"))

def _check_token_freshness() -> bool:
    token_location = os.environ.get("FABRIC_TOKEN_LOCATION")
    if not token_location:
        log("FABRIC_TOKEN_LOCATION is not set; did you source fabric_rc?")
        return False
    token_path = Path(token_location)
    payload = _load_token_payload(token_path)
    if payload is None:
        log(f"Token unreadable or missing at {token_path}")
        return False
    exp = payload.get("exp")
    if not exp:
        log("Token has no exp claim; cannot validate freshness.")
        return True
    exp_dt = datetime.fromtimestamp(int(exp), tz=timezone.utc)
    now = datetime.now(timezone.utc)
    if now >= exp_dt:
        log(f"Token expired at {exp_dt.isoformat()}. Download a new token.")
        return False
    minutes_left = int((exp_dt - now).total_seconds() / 60)
    log(f"Token OK; expires at {exp_dt.isoformat()} (~{minutes_left} minutes left).")
    return True

def main() -> int:
    # Common failures:
    # - you forgot to `source .../fabric_rc`
    # - token path wrong / token invalid
    # - project id wrong / not in project
    # - site capacity or quota issues
    log("Validating config/token before contacting FABRIC")
    if not _check_token_freshness():
        return 2
    log("Config/token valid")

    log("Initializing FablibManager (network call)")
    try:
        fablib = FablibManager()
    except Exception as e:
        log(f"FablibManager init failed: {e}")
        log("Did you source your fabric_rc in this shell?")
        return 2

    slice_name = f"wsl-demo-{int(time.time())}"

    # Pick a site you know works for you; change if needed.
    site = fablib.get_random_site()
    image = "default_ubuntu_20"

    try:
        log(f"Creating slice object {slice_name}")
        slc = fablib.new_slice(name=slice_name)

        # Minimal 1-node slice
        log("Adding node to slice")
        slc.add_node(name="node1", site=site, image=image, cores=2, ram=4, disk=10)

        log("Submitting slice (provisioning starts here)")
        slc.submit()

        # Poll state until stable-ish
        timeout_s = 600
        poll_s = 15
        start = time.time()

        while True:
            log("Polling slice state")
            state = slc.get_state()
            log(f"Slice state: {state}")
            if "Stable" in str(state) or "OK" in str(state):
                break
            if time.time() - start > timeout_s:
                log("Timed out waiting for stable; check FABRIC portal for sliver errors.")
                return 3
            time.sleep(poll_s)

        log("Slice is stable; printing summary:")
        print(slc)
        return 0

    except Exception as e:
        log(f"Slice creation failed: {e}")
        log("Common causes: wrong site name, quota/capacity, wrong image name, auth/config issues.")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
PY
