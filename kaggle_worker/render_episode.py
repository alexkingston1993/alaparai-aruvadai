import gc
import json
import os
import sys
from pathlib import Path
import torch
from diffusers import (
    StableDiffusionXLPipeline,
    EulerDiscreteScheduler,
    LTXImageToVideoPipeline,
)
from diffusers.utils import export_to_video, load_image

# Directories inside Kaggle VM
WORK_DIR = Path("/kaggle/working")
KEYFRAMES_DIR = WORK_DIR / "keyframes"
CLIPS_DIR = WORK_DIR / "clips"
KEYFRAMES_DIR.mkdir(parents=True, exist_ok=True)
CLIPS_DIR.mkdir(parents=True, exist_ok=True)

# Locate character bible & manifest
CAST_FILE_DATASET = Path("/kaggle/input/cast-assets/characters.json")
CAST_FILE_LOCAL = Path("characters.json")
MANIFEST_FILE = Path("episode_manifest.json")

def load_configs():
    if CAST_FILE_DATASET.exists():
        with open(CAST_FILE_DATASET, "r", encoding="utf-8") as f:
            cast = json.load(f)
    elif CAST_FILE_LOCAL.exists():
        with open(CAST_FILE_LOCAL, "r", encoding="utf-8") as f:
            cast = json.load(f)
    else:
        raise FileNotFoundError("Could not locate characters.json in dataset or working directory.")

    if not MANIFEST_FILE.exists():
        raise FileNotFoundError("episode_manifest.json not found in working directory.")

    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    return cast, manifest

def clear_vram():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

def render_keyframes(cast: dict, manifest: dict):
    print("=================================================================")
    print("STAGE 1: Keyframe Generation (SDXL-Lightning 4-Step)")
    print("=================================================================")

    pipe = StableDiffusionXLPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        torch_dtype=torch.float16,
        variant="fp16",
    ).to("cuda")

    # Check if local dataset has lightning lora, else load from huggingface
    local_lora = Path("/kaggle/input/cast-assets/sdxl_lightning_4step_lora.safetensors")
    if local_lora.exists():
        print(f"Loading SDXL-Lightning weights from dataset: {local_lora}")
        pipe.load_lora_weights(str(local_lora.parent), weight_name=local_lora.name)
    else:
        print("Downloading SDXL-Lightning LoRA from Hugging Face...")
        pipe.load_lora_weights("ByteDance/SDXL-Lightning", weight_name="sdxl_lightning_4step_lora.safetensors")

    pipe.fuse_lora()
    pipe.scheduler = EulerDiscreteScheduler.from_config(
        pipe.scheduler.config, timestep_spacing="trailing"
    )

    style_prefix = cast.get("style_prefix", "")

    for scene in manifest["scenes"]:
        idx = scene["scene_number"]
        char_id = scene["character_id"]
        char = cast["characters"].get(char_id, {})

        full_prompt = (
            f"{style_prefix}, {char.get('sdxl_base_prompt', '')}, "
            f"{scene.get('sdxl_scene_prompt', '')}, {scene.get('camera_shot', 'medium close-up')}, "
            f"{scene.get('emotion', 'expressive')} expression, sharp focus, cinema lighting"
        )

        print(f"Generating Keyframe {idx:02d} for {char.get('display_name', char_id)}...")
        image = pipe(
            prompt=full_prompt,
            num_inference_steps=4,
            guidance_scale=1.5,
            width=576,
            height=1024,
        ).images[0]

        out_path = KEYFRAMES_DIR / f"scene_{idx:02d}.png"
        image.save(out_path)
        print(f"-> Saved: {out_path}")

    del pipe
    clear_vram()

def animate_clips(manifest: dict):
    print("\n=================================================================")
    print("STAGE 2: Keyframe Animation (LTX-Video I2V)")
    print("=================================================================")

    pipe = LTXImageToVideoPipeline.from_pretrained(
        "Lightricks/LTX-Video",
        torch_dtype=torch.bfloat16,
    )
    # Enable model CPU offload and VAE tiling to stay safely under Kaggle 16GB VRAM
    pipe.enable_model_cpu_offload()
    pipe.vae.enable_tiling()

    for scene in manifest["scenes"]:
        idx = scene["scene_number"]
        img_path = KEYFRAMES_DIR / f"scene_{idx:02d}.png"
        if not img_path.exists():
            print(f"Skipping scene {idx:02d}, keyframe missing.")
            continue

        image = load_image(str(img_path))
        # 24 fps (LTX requires frame count = 8k + 1)
        dur = scene.get("duration_sec", 4)
        num_frames = 97 if dur >= 4 else 73

        print(f"Animating Scene {idx:02d} ({num_frames} frames)...")
        video_frames = pipe(
            image=image,
            prompt=scene.get("ltx_motion_prompt", "expressive head movement, talking mouth, comedic reaction"),
            negative_prompt="worst quality, blurry, jittery, morphing face, extra limbs, deformed",
            width=576,
            height=1024,
            num_frames=num_frames,
            num_inference_steps=8,
            guidance_scale=3.0,
        ).frames[0]

        out_mp4 = CLIPS_DIR / f"scene_{idx:02d}.mp4"
        export_to_video(video_frames, str(out_mp4), fps=24)
        print(f"-> Saved clip: {out_mp4}")

    del pipe
    clear_vram()

if __name__ == "__main__":
    cast, manifest = load_configs()
    render_keyframes(cast, manifest)
    animate_clips(manifest)
    print("\nAll scenes rendered successfully! Outputs in /kaggle/working/clips/")
