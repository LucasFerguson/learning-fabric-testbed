#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fabrictestbed_extensions.fablib.fablib import FablibManager
from fabrictestbed_extensions.fablib.fablib import SliceState


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
    parser = argparse.ArgumentParser(
        description="List FABRIC slices with node management IPs and SSH commands."
    )
    parser.add_argument("--name", help="Only show slices matching this name")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include Dead/Closing slices (default: active only)",
    )
    parser.add_argument(
        "--project",
        action="store_true",
        help="Show project slices (not just your own)",
    )
    args = parser.parse_args()

    if not _check_token_freshness():
        return 2

    log("Initializing FablibManager (network call)")
    fablib = FablibManager()

    excludes = [] if args.all else [SliceState.Dead, SliceState.Closing]
    slices = fablib.get_slices(
        excludes=excludes,
        slice_name=args.name,
        user_only=not args.project,
        show_un_submitted=True,
    )

    if not slices:
        log("No slices found.")
        return 0

    for slc in slices:
        log(
            f'Slice "{slc.get_name()}" | ID {slc.get_slice_id()} | '
            f"State {slc.get_state()} | Lease End {slc.get_lease_end()}"
        )
        nodes = slc.get_nodes()
        if not nodes:
            print("  (no nodes)")
            continue
        for node in nodes:
            ip = node.get_management_ip() or "None"
            ssh = node.get_ssh_command()
            print(f"  {node.get_name():<12} ip={ip}  ssh=\"{ssh}\"")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
