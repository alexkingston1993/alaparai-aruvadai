import asyncio
import json
import subprocess
import sys
from pathlib import Path
import edge_tts
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent.parent
MANIFESTS_DIR = BASE_DIR / "manifests"
CHARACTERS_PATH = BASE_DIR / "config" / "characters.json"
OUTPUT_ROOT = BASE_DIR / "rendered_clips"
KEYFRAMES_DIR = BASE_DIR / "keyframes"
SFX_DIR = BASE_DIR / "assets" / "sfx"
BGM_PATH = BASE_DIR / "assets" / "bgm" / "comedy_loop.mp3"
BUILD_DIR = BASE_DIR / "build"
OUTPUT_DIR = BASE_DIR / "output"

BUILD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Free Microsoft Edge Neural voices for Tamil
VOICE_MAP = {
    "ta_IN_male_fast_high": "ta-IN-ValluvarNeural",
    "ta_IN_male_deep_warm": "ta-IN-ValluvarNeural",
    "ta_IN_male_dramatic": "ta-IN-ValluvarNeural",
    "ta_IN_female_fiery": "ta-IN-PallaviNeural",
}

FONT_PATHS = [
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Black.ttf",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
]

def get_font(size: int):
    for fp in FONT_PATHS:
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()

def run_cmd(cmd: list[str]):
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(f"Command failed: {' '.join(cmd)}\nError: {res.stderr}")
        raise RuntimeError(res.stderr)

def get_duration(file_path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())

async def generate_tts(text: str, voice_profile: dict, out_mp3: Path):
    voice = VOICE_MAP.get(voice_profile.get("tts_voice_id", ""), "ta-IN-ValluvarNeural")
    pitch = voice_profile.get("pitch", "+0Hz").replace("%", "Hz")
    speed_float = float(voice_profile.get("speed", "1.0"))
    rate_pct = int((speed_float - 1.0) * 100)
    rate = f"{rate_pct:+d}%"

    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(str(out_mp3))

def create_subtitle_overlay(text: str, out_png: Path, hook_text: str = None):
    """Creates a transparent 1080x1920 PNG overlay with viral subtitles and hook banner."""
    img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Top Hook Banner (if present for scene 1)
    if hook_text:
        hook_font = get_font(46)
        hook_bbox = draw.textbbox((540, 240), hook_text, font=hook_font, anchor="mm")
        pad_x, pad_y = 30, 16
        pill_box = (
            max(40, hook_bbox[0] - pad_x),
            hook_bbox[1] - pad_y,
            min(1040, hook_bbox[2] + pad_x),
            hook_bbox[3] + pad_y
        )
        draw.rounded_rectangle(pill_box, radius=20, fill=(210, 20, 30, 235), outline=(255, 255, 255, 255), width=3)
        draw.text((540, 240), hook_text, font=hook_font, fill=(255, 255, 255, 255), anchor="mm")

    # 2. Viral Tanglish Subtitle (Yellow with thick black outline)
    sub_font = get_font(56)

    # Word wrap text if line is long
    words = text.split()
    lines = []
    current_line = []
    for w in words:
        current_line.append(w)
        test_line = " ".join(current_line)
        bbox = draw.textbbox((0, 0), test_line, font=sub_font)
        if (bbox[2] - bbox[0]) > 940:
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [w]
    if current_line:
        lines.append(" ".join(current_line))

    # Draw lines near bottom (y ~ 1450-1600)
    start_y = 1500 - (len(lines) * 35)
    for i, line in enumerate(lines):
        y_pos = start_y + (i * 70)
        # Thick stroke outline for viral readability
        draw.text(
            (540, y_pos),
            line,
            font=sub_font,
            fill=(255, 235, 0, 255),
            stroke_width=6,
            stroke_fill=(0, 0, 0, 255),
            anchor="mm"
        )

    img.save(out_png)

def find_clip(ep_id: str, scene_num: int) -> Path:
    candidates = [
        OUTPUT_ROOT / ep_id / "clips" / f"scene_{scene_num:02d}.mp4",
        OUTPUT_ROOT / ep_id / f"scene_{scene_num:02d}.mp4",
        OUTPUT_ROOT / "clips" / f"scene_{scene_num:02d}.mp4",
        KEYFRAMES_DIR / f"scene_{scene_num:02d}.mp4",
    ]
    for c in candidates:
        if c.exists():
            return c

    # Fallback: check if a rendered PNG keyframe was downloaded
    img_candidates = [
        OUTPUT_ROOT / ep_id / "keyframes" / f"scene_{scene_num:02d}.png",
        OUTPUT_ROOT / ep_id / f"scene_{scene_num:02d}.png",
        KEYFRAMES_DIR / f"scene_{scene_num:02d}.png",
    ]
    for img in img_candidates:
        if img.exists():
            out_clip = OUTPUT_ROOT / ep_id / "clips" / f"scene_{scene_num:02d}.mp4"
            out_clip.parent.mkdir(parents=True, exist_ok=True)
            cmd = [
                "ffmpeg", "-y", "-loop", "1", "-i", str(img),
                "-c:v", "libx264", "-t", "5", "-pix_fmt", "yuv420p",
                "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
                str(out_clip)
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return out_clip

    return candidates[0]

async def assemble_episode(ep_id: str = "ep_001"):
    manifest_file = MANIFESTS_DIR / f"{ep_id}_manifest.json"
    if not manifest_file.exists():
        manifest_file = BASE_DIR / "kaggle_worker" / "episode_manifest.json"

    if not manifest_file.exists():
        print(f"ERROR: Manifest for {ep_id} not found.")
        sys.exit(1)

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    cast = json.loads(CHARACTERS_PATH.read_text(encoding="utf-8"))["characters"]
    hook_text = manifest.get("seo_metadata", {}).get("hook_text", "")

    print(f"\n=======================================================")
    print(f"🎬 Assembling {ep_id}: {manifest.get('title_tanglish', '')}")
    print(f"=======================================================\n")

    processed_scenes = []

    for scene in manifest["scenes"]:
        idx = scene["scene_number"]
        char_id = scene["character_id"]
        raw_clip = find_clip(ep_id, idx)

        if not raw_clip.exists():
            print(f"Warning: {raw_clip} not found. Skipping scene {idx:02d}.")
            continue

        tts_mp3 = BUILD_DIR / f"{ep_id}_scene_{idx:02d}_tts.mp3"
        overlay_png = BUILD_DIR / f"{ep_id}_scene_{idx:02d}_sub.png"
        scene_out = BUILD_DIR / f"{ep_id}_scene_{idx:02d}_final.mp4"

        # 1. Generate Voice
        voice_prof = cast.get(char_id, {}).get("voice_profile", {})
        await generate_tts(scene["dialogue"]["tamil_text"], voice_prof, tts_mp3)

        audio_dur = get_duration(tts_mp3) + 0.25
        video_dur = get_duration(raw_clip)
        pts_factor = audio_dur / max(video_dur, 0.1)

        # 2. Render Subtitle & Hook Overlay PNG
        scene_hook = hook_text if idx == 1 else None
        create_subtitle_overlay(scene["dialogue"]["tanglish_subtitle"], overlay_png, scene_hook)

        # 3. Mix SFX and assemble via overlay filter
        sfx_cue = scene.get("sfx_cue", "")
        sfx_file = SFX_DIR / f"{sfx_cue}.mp3"

        if sfx_file.exists():
            cmd = [
                "ffmpeg", "-y",
                "-i", str(raw_clip),
                "-i", str(overlay_png),
                "-i", str(tts_mp3),
                "-i", str(sfx_file),
                "-filter_complex",
                f"[0:v]setpts={pts_factor:.4f}*PTS,scale=1080:1920:flags=lanczos[v0];"
                f"[v0][1:v]overlay=0:0[v];"
                f"[2:a]apad=pad_dur=0.25[voice];"
                f"[3:a]volume=0.55[sfx];"
                f"[voice][sfx]amix=inputs=2:duration=first[a]",
                "-map", "[v]", "-map", "[a]",
                "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                "-c:a", "aac", "-b:a", "192k", "-t", f"{audio_dur:.2f}",
                str(scene_out)
            ]
        else:
            cmd = [
                "ffmpeg", "-y",
                "-i", str(raw_clip),
                "-i", str(overlay_png),
                "-i", str(tts_mp3),
                "-filter_complex",
                f"[0:v]setpts={pts_factor:.4f}*PTS,scale=1080:1920:flags=lanczos[v0];"
                f"[v0][1:v]overlay=0:0[v]",
                "-map", "[v]", "-map", "2:a",
                "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                "-c:a", "aac", "-b:a", "192k", "-t", f"{audio_dur:.2f}",
                str(scene_out)
            ]

        run_cmd(cmd)
        processed_scenes.append(scene_out)
        print(f"✓ Assembled Scene {idx:02d} ({audio_dur:.2f}s)")

    if not processed_scenes:
        print(f"No scenes processed for {ep_id}. Check outputs.")
        return

    # 4. Concatenate
    concat_txt = BUILD_DIR / f"{ep_id}_concat.txt"
    concat_txt.write_text(
        "\n".join([f"file '{p.resolve()}'" for p in processed_scenes]),
        encoding="utf-8"
    )
    merged_mp4 = BUILD_DIR / f"{ep_id}_merged.mp4"
    run_cmd([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_txt), "-c", "copy", str(merged_mp4)
    ])

    # 5. Background Music Layer
    final_mp4 = OUTPUT_DIR / f"{ep_id}_final.mp4"
    if BGM_PATH.exists():
        run_cmd([
            "ffmpeg", "-y",
            "-i", str(merged_mp4),
            "-stream_loop", "-1", "-i", str(BGM_PATH),
            "-filter_complex", "[1:a]volume=0.12[bgm];[0:a][bgm]amix=inputs=2:duration=first[a]",
            "-map", "0:v", "-map", "[a]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            str(final_mp4)
        ])
    else:
        merged_mp4.rename(final_mp4)

    print(f"\n=======================================================")
    print(f"🎉 Episode assembly complete! Video saved to:")
    print(f"{final_mp4}")
    print(f"=======================================================\n")

if __name__ == "__main__":
    ep = sys.argv[1] if len(sys.argv) > 1 else "ep_001"
    asyncio.run(assemble_episode(ep))
