import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MANIFESTS_DIR = BASE_DIR / "manifests"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_ROOT = BASE_DIR / "rendered_clips"
KEYFRAMES_DIR = BASE_DIR / "keyframes"

def generate_thumbnail(ep_id: str = "ep_001"):
    manifest_file = MANIFESTS_DIR / f"{ep_id}_manifest.json"
    if not manifest_file.exists():
        manifest_file = BASE_DIR / "kaggle_worker" / "episode_manifest.json"

    if not manifest_file.exists():
        print(f"ERROR: Manifest for {ep_id} not found.")
        sys.exit(1)

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    title_tamil = manifest.get("title_tamil", "வெள்ளை புலி வேந்தன்")
    title_tanglish = manifest.get("title_tanglish", "Vellai Puli Vendhan")

    # Find candidate image
    candidate_img = None
    for p in [
        KEYFRAMES_DIR / f"{ep_id}_scene_01.png",
        OUTPUT_ROOT / ep_id / "keyframes" / "scene_01.png",
        BASE_DIR / "assets" / "cast_references" / "vendhan_poor.png"
    ]:
        if p.exists():
            candidate_img = p
            break

    out_thumb = OUTPUT_DIR / f"{ep_id}_thumbnail.jpg"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Use FFmpeg to composite high-contrast vertical thumbnail (1080x1920) with dramatic text
    if candidate_img:
        cmd = [
            "ffmpeg", "-y",
            "-i", str(candidate_img),
            "-vf",
            "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            "eq=contrast=1.2:saturation=1.35,"
            f"drawtext=text='{title_tanglish}':font='Arial-Bold':fontsize=72:fontcolor=yellow:borderw=8:bordercolor=black:x=(w-text_w)/2:y=180,"
            "drawtext=text='PART 1':font='Arial-Black':fontsize=110:fontcolor=white:borderw=10:bordercolor=red:x=(w-text_w)/2:y=280",
            "-q:v", "2",
            str(out_thumb)
        ]
        subprocess.run(cmd, check=True)
        print(f"Generated thumbnail: {out_thumb}")
    else:
        print(f"No keyframe image found yet. Thumbnail can be generated after keyframes/clips are rendered.")

if __name__ == "__main__":
    ep = sys.argv[1] if len(sys.argv) > 1 else "ep_001"
    generate_thumbnail(ep)
