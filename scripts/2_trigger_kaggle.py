import shutil
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MANIFESTS_DIR = BASE_DIR / "manifests"
KAGGLE_DIR = BASE_DIR / "kaggle_worker"
OUTPUT_ROOT = BASE_DIR / "rendered_clips"
KERNEL_ID = "YOUR_KAGGLE_USERNAME/tamil-ai-webseries-worker"  # Update with your Kaggle username


def run_episode(ep_id: str, poll_seconds: int = 60):
    src_manifest = MANIFESTS_DIR / f"{ep_id}_manifest.json"
    if not src_manifest.exists():
        raise FileNotFoundError(f"Manifest not found: {src_manifest}")

    # Copy target episode manifest into kaggle_worker/episode_manifest.json
    shutil.copy2(src_manifest, KAGGLE_DIR / "episode_manifest.json")
    print(f"[{ep_id}] Staged manifest in {KAGGLE_DIR / 'episode_manifest.json'}")

    # Push to Kaggle GPU
    subprocess.run(["kaggle", "kernels", "push", "-p", str(KAGGLE_DIR)], check=True)
    print(f"[{ep_id}] Pushed kernel to Kaggle. Polling status every {poll_seconds}s...")

    while True:
        res = subprocess.run(
            ["kaggle", "kernels", "status", KERNEL_ID],
            capture_output=True, text=True, check=True
        )
        status_line = res.stdout.strip()
        print(f"[{ep_id}] {status_line}")

        if "complete" in status_line.lower():
            break
        if "error" in status_line.lower() or "cancel" in status_line.lower():
            raise RuntimeError(f"Kaggle run failed: {status_line}")

        time.sleep(poll_seconds)

    # Pull rendered clips
    ep_out = OUTPUT_ROOT / ep_id
    ep_out.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["kaggle", "kernels", "output", KERNEL_ID, "-p", str(ep_out)],
        check=True
    )
    print(f"[{ep_id}] Downloaded rendered clips to {ep_out}")


if __name__ == "__main__":
    ep = sys.argv[1] if len(sys.argv) > 1 else "ep_001"
    run_episode(ep)
