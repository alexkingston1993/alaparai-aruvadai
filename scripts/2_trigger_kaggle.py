import shutil
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MANIFESTS_DIR = BASE_DIR / "manifests"
CONFIG_DIR = BASE_DIR / "config"
KAGGLE_DIR = BASE_DIR / "kaggle_worker"
OUTPUT_ROOT = BASE_DIR / "rendered_clips"
KERNEL_ID = "alexytcreative/alaparai-aruvadai-worker"

def get_kaggle_cmd() -> str:
    # Check if kaggle is in system PATH
    system_kaggle = shutil.which("kaggle")
    if system_kaggle:
        return system_kaggle
    
    # Check virtual environment from adjacent workspace folder
    adjacent_venv_kaggle = Path("/Users/apple/Documents/Antigravity/untitled folder/.venv/bin/kaggle")
    if adjacent_venv_kaggle.exists():
        return str(adjacent_venv_kaggle)
    
    # Check user home bin
    user_kaggle = Path.home() / ".local" / "bin" / "kaggle"
    if user_kaggle.exists():
        return str(user_kaggle)
        
    return "kaggle"

KAGGLE_CMD = get_kaggle_cmd()

def run_episode(ep_id: str, poll_seconds: int = 45):
    src_manifest = MANIFESTS_DIR / f"{ep_id}_manifest.json"
    if not src_manifest.exists():
        raise FileNotFoundError(f"Manifest not found: {src_manifest}")

    # Stage episode manifest
    shutil.copy2(src_manifest, KAGGLE_DIR / "episode_manifest.json")
    print(f"[{ep_id}] Staged manifest in {KAGGLE_DIR / 'episode_manifest.json'}")

    # Stage characters.json so it gets uploaded directly with the kernel
    characters_file = CONFIG_DIR / "characters.json"
    if characters_file.exists():
        shutil.copy2(characters_file, KAGGLE_DIR / "characters.json")
        print(f"[{ep_id}] Staged {characters_file} in {KAGGLE_DIR / 'characters.json'}")

    # Push to Kaggle GPU
    print(f"[{ep_id}] Pushing kernel to Kaggle using '{KAGGLE_CMD}'...")
    res = subprocess.run([KAGGLE_CMD, "kernels", "push", "-p", str(KAGGLE_DIR)], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error pushing to Kaggle:\n{res.stderr}\n{res.stdout}")
        sys.exit(1)
        
    print(f"[{ep_id}] Pushed kernel successfully! Polling status every {poll_seconds}s...")

    while True:
        res = subprocess.run(
            [KAGGLE_CMD, "kernels", "status", KERNEL_ID],
            capture_output=True, text=True
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
    print(f"[{ep_id}] Downloading rendered outputs to {ep_out}...")
    subprocess.run(
        [KAGGLE_CMD, "kernels", "output", KERNEL_ID, "-p", str(ep_out)],
        check=True
    )
    print(f"[{ep_id}] Successfully downloaded clips to {ep_out}!")

if __name__ == "__main__":
    ep = sys.argv[1] if len(sys.argv) > 1 else "ep_001"
    run_episode(ep)
