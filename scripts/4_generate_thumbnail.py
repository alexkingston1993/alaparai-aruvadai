import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

BASE_DIR = Path(__file__).resolve().parent.parent
MANIFESTS_DIR = BASE_DIR / "manifests"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_ROOT = BASE_DIR / "rendered_clips"
KEYFRAMES_DIR = BASE_DIR / "keyframes"

FONT_PATHS = [
    "/System/Library/Fonts/Supplemental/Arial Black.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/HelveticaNeue.ttc",
]

def get_font(size: int):
    for fp in FONT_PATHS:
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()

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
        OUTPUT_ROOT / ep_id / "keyframes" / "scene_01.png",
        OUTPUT_ROOT / ep_id / "keyframes" / "scene_06.png",
        KEYFRAMES_DIR / f"{ep_id}_scene_01.png",
        KEYFRAMES_DIR / "scene_01.png",
    ]:
        if p.exists():
            candidate_img = p
            break

    out_thumb = OUTPUT_DIR / f"{ep_id}_thumbnail.jpg"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not candidate_img:
        print("No keyframe image found to generate thumbnail.")
        return

    # Open and enhance contrast & color saturation
    base_img = Image.open(candidate_img).convert("RGB")
    base_img = base_img.resize((1080, 1920), Image.Resampling.LANCZOS)

    enhancer_color = ImageEnhance.Color(base_img)
    base_img = enhancer_color.enhance(1.3)
    enhancer_contrast = ImageEnhance.Contrast(base_img)
    base_img = enhancer_contrast.enhance(1.2)

    draw = ImageDraw.Draw(base_img)

    # 1. Top Badging: "EPISODE 1" or "PART 1"
    badge_font = get_font(72)
    badge_text = "PART 1: AVAMAANAM! 😢"
    draw.rounded_rectangle((60, 140, 1020, 260), radius=25, fill=(220, 20, 30), outline=(255, 255, 255), width=5)
    draw.text((540, 200), badge_text, font=badge_font, fill=(255, 255, 255), stroke_width=4, stroke_fill=(0, 0, 0), anchor="mm")

    # 2. Viral Bottom Banner: Hook
    hook_font = get_font(56)
    hook_text = "வெள்ளை புலி வேந்தன்"
    draw.text((540, 1680), hook_text, font=hook_font, fill=(255, 240, 0), stroke_width=6, stroke_fill=(0, 0, 0), anchor="mm")

    base_img.save(out_thumb, "JPEG", quality=95)
    print(f"✓ Generated high-contrast viral thumbnail: {out_thumb}")

if __name__ == "__main__":
    ep = sys.argv[1] if len(sys.argv) > 1 else "ep_001"
    generate_thumbnail(ep)
