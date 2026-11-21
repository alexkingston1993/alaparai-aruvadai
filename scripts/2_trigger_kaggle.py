import json
import os
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
KAGGLE_WORKER_DIR = BASE_DIR / "kaggle_worker"
CLIPS_OUTPUT_DIR = BASE_DIR / "rendered_clips"
METADATA_FILE = KAGGLE_WORKER_DIR / "kernel-metadata.json"

def check_kaggle_cli():
    try:
        subprocess.run(["kaggle", "--version"], check=True, capture_output=True, text=True)
    except FileNotFoundError:
        print("ERROR: 'kaggle' CLI is not installed or not in PATH.")
        print("Install via: pip install kaggle")
        print("Place your API token at ~/.kaggle/kaggle.json")
        sys.exit(1)

def get_kernel_id() -> str:
    if not METADATA_FILE.exists():
        print(f"ERROR: {METADATA_FILE} not found.")
        sys.exit(1)
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        meta = json.load(f)
    kernel_id = meta.get("id")
    if "YOUR_KAGGLE_USERNAME" in kernel_id:
        print("ERROR: Replace 'YOUR_KAGGLE_USERNAME' in kaggle_worker/kernel-metadata.json with your actual Kaggle username.")
        sys.exit(1)
    return kernel_id

def push_kernel():
    print(f"Pushing notebook kernel from {KAGGLE_WORKER_DIR}...")
    res = subprocess.run(["kaggle", "kernels", "push", "-p", str(KAGGLE_WORKER_DIR)], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Kaggle push failed:\n{res.stderr}\n{res.stdout}")
        sys.exit(1)
    print("Kernel pushed successfully! Execution started in Kaggle cloud.")

def monitor_kernel(kernel_id: str, poll_interval_sec: int = 45, max_wait_min: int = 40):
    start_time = time.time()
    max_seconds = max_wait_min * 60
    print(f"Monitoring execution of {kernel_id} (polling every {poll_interval_sec}s)...")

    while True:
        elapsed = int(time.time() - start_time)
        if elapsed > max_seconds:
            print(f"TIMEOUT: Exceeded maximum wait time of {max_wait_min} minutes.")
            sys.exit(1)

        res = subprocess.run(["kaggle", "kernels", "status", kernel_id], capture_output=True, text=True)
        status_line = res.stdout.strip()
        print(f"[{elapsed//60:02d}m {elapsed%60:02d}s] Status: {status_line}")

        if "complete" in status_line.lower():
            print("Rendering complete!")
            break
        elif "error" in status_line.lower():
            print(f"ERROR in Kaggle kernel execution: {status_line}")
            sys.exit(1)
        elif "queued" in status_line.lower() or "running" in status_line.lower():
            time.sleep(poll_interval_sec)
        else:
            time.sleep(poll_interval_sec)

def pull_output(kernel_id: str):
    CLIPS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading rendered outputs to {CLIPS_OUTPUT_DIR}...")
    res = subprocess.run(["kaggle", "kernels", "output", kernel_id, "-p", str(CLIPS_OUTPUT_DIR)], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Failed to download outputs:\n{res.stderr}")
        sys.exit(1)
    print("Downloaded rendered clips successfully!")

def main():
    check_kaggle_cli()
    kernel_id = get_kernel_id()
    push_kernel()
    monitor_kernel(kernel_id)
    pull_output(kernel_id)

if __name__ == "__main__":
    main()
