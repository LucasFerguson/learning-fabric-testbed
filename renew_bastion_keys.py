#!/usr/bin/env python3
from __future__ import annotations

import os
from datetime import datetime

from fabrictestbed_extensions.fablib.fablib import FablibManager


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def main() -> int:
    if "FABRIC_TOKEN_LOCATION" not in os.environ:
        log("FABRIC_TOKEN_LOCATION is not set; did you source fabric_rc?")
        return 2

    log("Initializing FablibManager (network call)")
    fablib = FablibManager()

    log("Verifying configuration and renewing bastion keys if needed")
    fablib.verify_and_configure()

    log("Done. SSH config should be updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
