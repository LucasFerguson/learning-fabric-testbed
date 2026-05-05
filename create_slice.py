#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import tarfile
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from fabrictestbed_extensions.fablib.fablib import FablibManager


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


@contextmanager
def log_step(title: str):
    log(f"{title}...")
    start = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start
        log(f"{title} done in {elapsed:.1f}s")


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


def _check_file_env(var_name: str, label: str) -> bool:
    path = os.environ.get(var_name)
    if not path:
        log(f"{label} env var {var_name} is not set.")
        return False
    p = Path(path)
    if not p.exists():
        log(f"{label} file missing at {p}")
        return False
    return True


def _pack_payload(payload_dir: Path) -> Path:
    """Tar-gz the payload directory into a temp file; return its path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False)
    tmp.close()
    log(f"Packing {payload_dir} -> {tmp.name}")
    with tarfile.open(tmp.name, "w:gz") as tar:
        for entry in sorted(payload_dir.iterdir()):
            log(f"  Adding {entry.name}")
            tar.add(entry, arcname=entry.name)
    size_kb = Path(tmp.name).stat().st_size // 1024
    log(f"Payload tarball ready ({size_kb} KB)")
    return Path(tmp.name)


def _upload_and_run_payload(node, payload_dir: Path) -> bool:
    """
    Upload payload/ to the node, make scripts executable, and run setup.sh.
    Returns True on success.
    """
    remote_payload = "/home/ubuntu/payload"
    remote_tar = "/tmp/payload.tar.gz"
    remote_log = "/home/ubuntu/setup.log"

    # ── pack ──────────────────────────────────────────────────────────
    with log_step("Packing payload directory"):
        tarball = _pack_payload(payload_dir)

    try:
        # ── wait for SSH ──────────────────────────────────────────────
        log("Waiting for SSH to become available on node...")
        ssh_ready = False
        for attempt in range(1, 13):  # up to ~2 minutes
            try:
                stdout, stderr = node.execute("echo ssh-ok", quiet=True)
                if "ssh-ok" in stdout:
                    log(f"SSH ready (attempt {attempt})")
                    ssh_ready = True
                    break
            except Exception as exc:
                log(f"  SSH attempt {attempt}/12 failed: {exc}")
            time.sleep(10)

        if not ssh_ready:
            log("ERROR: SSH never became ready; giving up on payload upload.")
            return False

        # ── remote system info (quick sanity check) ───────────────────
        log("Remote system info:")
        for cmd, label in [
            ("hostname", "hostname"),
            ("uname -r", "kernel"),
            ("df -h / | tail -1", "disk /"),
        ]:
            try:
                stdout, _ = node.execute(cmd, quiet=True)
                log(f"  {label}: {stdout.strip()}")
            except Exception as exc:
                log(f"  {label}: could not read ({exc})")

        # ── upload tarball ────────────────────────────────────────────
        with log_step(f"Uploading payload tarball to node:{remote_tar}"):
            node.upload_file(str(tarball), remote_tar)

        # ── extract ───────────────────────────────────────────────────
        with log_step(f"Extracting tarball to {remote_payload}"):
            stdout, stderr = node.execute(
                f"mkdir -p {remote_payload} && "
                f"tar -xzf {remote_tar} -C {remote_payload} && "
                f"echo extract-ok",
                quiet=True,
            )
            if "extract-ok" not in stdout:
                log(f"ERROR: extraction may have failed.\n  stdout={stdout}\n  stderr={stderr}")
                return False
            log("Extraction succeeded")

        # ── list contents for debugging ───────────────────────────────
        log("Remote payload directory contents:")
        stdout, _ = node.execute(f"ls -lh {remote_payload}", quiet=True)
        for line in stdout.strip().splitlines():
            log(f"  {line}")

        # ── chmod ─────────────────────────────────────────────────────
        with log_step("Making scripts executable"):
            node.execute(f"chmod +x {remote_payload}/*.sh", quiet=True)

        # ── run setup.sh ──────────────────────────────────────────────
        setup_script = f"{remote_payload}/setup.sh"
        log(f"Running {setup_script} on node (this may take a minute)...")
        start = time.time()
        stdout, stderr = node.execute(
            f"bash {setup_script}",
            quiet=False,  # stream to local stdout as it runs
        )
        elapsed = time.time() - start
        log(f"setup.sh finished in {elapsed:.1f}s")

        if stderr and stderr.strip():
            log(f"setup.sh stderr:\n{stderr}")

        # ── fetch and print the remote log file ───────────────────────
        log(f"Fetching remote log file {remote_log} ...")
        try:
            local_log = Path(tempfile.mktemp(suffix="_setup.log"))
            node.download_file(str(local_log), remote_log)
            log("=== BEGIN remote setup.log ===")
            print(local_log.read_text(), flush=True)
            log("=== END remote setup.log ===")
            local_log.unlink(missing_ok=True)
        except Exception as exc:
            log(f"Could not download setup.log: {exc}")
            log("(The script output above should still show what happened.)")

        return True

    finally:
        # clean up local tarball regardless of outcome
        try:
            tarball.unlink(missing_ok=True)
        except Exception:
            pass


def main() -> int:
    # ── pre-flight checks ─────────────────────────────────────────────
    log("Validating config/token before contacting FABRIC")
    if not _check_token_freshness():
        return 2
    log("Config/token valid")

    _check_file_env("FABRIC_BASTION_KEY_LOCATION", "Bastion key")
    _check_file_env("FABRIC_SLICE_PRIVATE_KEY_FILE", "Slice private key")
    _check_file_env("FABRIC_SLICE_PUBLIC_KEY_FILE", "Slice public key")

    payload_dir = Path(__file__).parent / "payload"
    if not payload_dir.is_dir():
        log(f"ERROR: payload/ directory not found at {payload_dir}")
        return 2
    payload_scripts = list(payload_dir.glob("*.sh"))
    if not payload_scripts:
        log(f"WARNING: no .sh scripts found in {payload_dir}")
    else:
        log(f"Payload directory OK ({len(payload_scripts)} script(s): "
            f"{', '.join(s.name for s in payload_scripts)})")

    # ── init fablib ───────────────────────────────────────────────────
    log("Initializing FablibManager (network call)")
    try:
        fablib = FablibManager()
    except Exception as e:
        log(f"FablibManager init failed: {e}")
        log("Did you source your fabric_rc in this shell?")
        return 2

    slice_name = f"wsl-demo-{int(time.time())}"
    site = fablib.get_random_site()
    image = "default_ubuntu_20"

    log(f"Slice name : {slice_name}")
    log(f"Site       : {site}")
    log(f"Image      : {image}")

    try:
        with log_step(f"Creating slice object {slice_name}"):
            slc = fablib.new_slice(name=slice_name)

        with log_step("Adding node to slice"):
            node = slc.add_node(name="node1", site=site, image=image, cores=2, ram=4, disk=10)

        with log_step("Submitting slice (provisioning starts now)"):
            slc.submit()

        # ── wait for stable ───────────────────────────────────────────
        timeout_s = 600
        poll_s = 15
        start = time.time()

        with log_step("Waiting for slice to become stable"):
            while True:
                state = slc.get_state()
                log(f"Slice state: {state}")
                if "Stable" in str(state) or "OK" in str(state):
                    break
                if time.time() - start > timeout_s:
                    log("Timed out waiting for stable; check FABRIC portal for sliver errors.")
                    return 3
                time.sleep(poll_s)

        log("Slice is stable:")
        print(slc)

        # ── refresh node handle after provisioning ────────────────────
        slc.update()
        node = slc.get_node("node1")
        log(f"Node management IP : {node.get_management_ip()}")

        # ── upload payload and run setup.sh ───────────────────────────
        log("")
        log("=== Payload upload and remote setup ===")
        success = _upload_and_run_payload(node, payload_dir)
        if not success:
            log("Payload setup encountered errors; slice remains up for inspection.")
            return 4

        log("")
        log("All steps completed successfully.")
        return 0

    except Exception as e:
        log(f"Slice creation failed: {e}")
        log("Common causes: wrong site name, quota/capacity, wrong image name, auth/config issues.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
