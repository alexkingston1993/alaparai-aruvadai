import json
import re
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
KERNEL_ID = "alexytcreative/vellai-puli-vendhan-worker"

def get_kaggle_cmd() -> str:
    system_kaggle = shutil.which("kaggle")
    if system_kaggle:
        return system_kaggle
    
    adjacent_venv_kaggle = Path("/Users/apple/Documents/Antigravity/untitled folder/.venv/bin/kaggle")
    if adjacent_venv_kaggle.exists():
        return str(adjacent_venv_kaggle)
    
    user_kaggle = Path.home() / ".local" / "bin" / "kaggle"
    if user_kaggle.exists():
        return str(user_kaggle)
        
    return "kaggle"

KAGGLE_CMD = get_kaggle_cmd()

def stage_and_push(ep_id: str, poll_seconds: int = 40):
    src_manifest = MANIFESTS_DIR / f"{ep_id}_manifest.json"
    if not src_manifest.exists():
        raise FileNotFoundError(f"Manifest not found: {src_manifest}")

    manifest_data = json.loads(src_manifest.read_text(encoding="utf-8"))
    cast_data = json.loads((CONFIG_DIR / "characters.json").read_text(encoding="utf-8"))

    # Also save local copies in kaggle_worker folder
    shutil.copy2(src_manifest, KAGGLE_DIR / "episode_manifest.json")
    shutil.copy2(CONFIG_DIR / "characters.json", KAGGLE_DIR / "characters.json")

    # Embed data directly into render_episode.py so it never depends on external files
    worker_script_path = KAGGLE_DIR / "render_episode.py"
    script_text = worker_script_path.read_text(encoding="utf-8")

    cast_json_str = json.dumps(cast_data, ensure_ascii=False, indent=2)
    manifest_json_str = json.dumps(manifest_data, ensure_ascii=False, indent=2)

    script_text = re.sub(
        r"EMBEDDED_CAST\s*=\s*\{.*?\n\}\n\nEMBEDDED_MANIFEST",
        f"EMBEDDED_CAST = {cast_json_str}\n\nEMBEDDED_MANIFEST",
        script_text,
        flags=re.DOTALL
    )
    script_text = re.sub(
        r"EMBEDDED_MANIFEST\s*=\s*\{.*?\n\}\n\n# Load cast bible",
        f"EMBEDDED_MANIFEST = {manifest_json_str}\n\n# Load cast bible",
        script_text,
        flags=re.DOTALL
    )

    worker_script_path.write_text(script_text, encoding="utf-8")
    print(f"[{ep_id}] Staged isolated worker code in {worker_script_path}")

    # Push to Kaggle GPU
    print(f"[{ep_id}] Pushing kernel to Kaggle GPU ({KERNEL_ID})...")
    res = subprocess.run([KAGGLE_CMD, "kernels", "push", "-p", str(KAGGLE_DIR)], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error pushing to Kaggle:\n{res.stderr}\n{res.stdout}")
        sys.exit(1)
        
    print(f"[{ep_id}] Kernel pushed successfully! Status: running in Kaggle cloud...")

    # Poll status
    start_time = time.time()
    while True:
        res = subprocess.run(
            [KAGGLE_CMD, "kernels", "status", KERNEL_ID],
            capture_output=True, text=True
        )
        status_line = res.stdout.strip()
        elapsed = int(time.time() - start_time)
        print(f"[{ep_id} | {elapsed//60:02d}m {elapsed%60:02d}s] {status_line}")

        if "complete" in status_line.lower():
            print(f"[{ep_id}] Cloud rendering complete!")
            break
        if "error" in status_line.lower() or "cancel" in status_line.lower():
            subprocess.run([KAGGLE_CMD, "kernels", "output", KERNEL_ID, "-p", "/tmp/kaggle_err"], capture_output=True)
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

    # Auto-assemble the episode video
    print(f"\n[{ep_id}] Automatically starting final video assembly...")
    assemble_script = BASE_DIR / "scripts" / "3_assemble_video.py"
    subprocess.run([sys.executable, str(assemble_script), ep_id], check=True)

    # Auto-generate the thumbnail
    thumb_script = BASE_DIR / "scripts" / "4_generate_thumbnail.py"
    if thumb_script.exists():
        subprocess.run([sys.executable, str(thumb_script), ep_id], check=False)

if __name__ == "__main__":
    ep = sys.argv[1] if len(sys.argv) > 1 else "ep_001"
    stage_and_push(ep)
