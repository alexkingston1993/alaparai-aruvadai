import asyncio
import json
import subprocess
import sys
from pathlib import Path
import edge_tts

BASE_DIR = Path(__file__).resolve().parent.parent
MANIFEST_PATH = BASE_DIR / "kaggle_worker" / "episode_manifest.json"
CHARACTERS_PATH = BASE_DIR / "config" / "characters.json"
CLIPS_DIR = BASE_DIR / "rendered_clips" / "clips"
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

def write_ass_subtitle(text: str, duration: float, out_ass: Path):
    """Generates viral yellow/white bold high-contrast subtitles for 9:16 vertical video."""
    h = int(duration // 3600)
    m = int((duration % 3600) // 60)
    s = duration % 60
    end_ts = f"{h}:{m:02d}:{s:05.2f}"

    ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Viral,Arial Black,68,&H0000FFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,3,2,60,60,320,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,{end_ts},Viral,,0,0,0,,{text}
"""
    out_ass.write_text(ass_content, encoding="utf-8")

async def assemble_episode():
    if not MANIFEST_PATH.exists():
        print(f"ERROR: {MANIFEST_PATH} not found. Run scripts/1_generate_script.py first.")
        sys.exit(1)

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    cast = json.loads(CHARACTERS_PATH.read_text(encoding="utf-8"))["characters"]
    ep_id = manifest["episode_id"]

    processed_scenes = []

    for scene in manifest["scenes"]:
        idx = scene["scene_number"]
        char_id = scene["character_id"]
        raw_clip = CLIPS_DIR / f"scene_{idx:02d}.mp4"

        # Fallback if raw clip is not yet downloaded
        if not raw_clip.exists():
            print(f"Warning: {raw_clip} not found in rendered_clips/clips. Make sure Kaggle job finished.")
            continue

        tts_mp3 = BUILD_DIR / f"scene_{idx:02d}_tts.mp3"
        ass_file = BUILD_DIR / f"scene_{idx:02d}.ass"
        scene_out = BUILD_DIR / f"scene_{idx:02d}_final.mp4"

        # 1. Generate Voice
        voice_prof = cast.get(char_id, {}).get("voice_profile", {})
        await generate_tts(scene["dialogue"]["tamil_text"], voice_prof, tts_mp3)

        audio_dur = get_duration(tts_mp3) + 0.25
        video_dur = get_duration(raw_clip)
        pts_factor = audio_dur / max(video_dur, 0.1)

        # 2. Subtitle
        write_ass_subtitle(scene["dialogue"]["tanglish_subtitle"], audio_dur, ass_file)

        # 3. SFX and Assembly
        sfx_cue = scene.get("sfx_cue", "")
        sfx_file = SFX_DIR / f"{sfx_cue}.mp3"
        ass_escaped = str(ass_file).replace("\\", "/").replace(":", "\\:")

        if sfx_file.exists():
            cmd = [
                "ffmpeg", "-y",
                "-i", str(raw_clip),
                "-i", str(tts_mp3),
                "-i", str(sfx_file),
                "-filter_complex",
                f"[0:v]setpts={pts_factor:.4f}*PTS,scale=1080:1920:flags=lanczos,ass='{ass_escaped}'[v];"
                f"[1:a]apad=pad_dur=0.25[voice];"
                f"[2:a]volume=0.55[sfx];"
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
                "-i", str(tts_mp3),
                "-vf", f"setpts={pts_factor:.4f}*PTS,scale=1080:1920:flags=lanczos,ass='{ass_escaped}'",
                "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                "-c:a", "aac", "-b:a", "192k", "-t", f"{audio_dur:.2f}",
                str(scene_out)
            ]

        run_cmd(cmd)
        processed_scenes.append(scene_out)
        print(f"Processed Scene {idx:02d} ({audio_dur:.2f}s)")

    if not processed_scenes:
        print("No scenes processed. Check clips directory.")
        return

    # 4. Concatenate
    concat_txt = BUILD_DIR / "concat.txt"
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
    asyncio.run(assemble_episode())
