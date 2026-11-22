import gc
import json
import os
import subprocess
import sys
from pathlib import Path

# 1. Force-upgrade diffusers & dependencies for real LTXImageToVideoPipeline
print("--- Installing latest diffusers & dependencies ---", flush=True)
subprocess.check_call([
    sys.executable, "-m", "pip", "install", "-q", "--upgrade",
    "git+https://github.com/huggingface/diffusers.git",
    "transformers", "accelerate", "sentencepiece", "imageio", "imageio-ffmpeg"
])
# Remove conflicting torchao so PEFT doesn't crash on older Kaggle image version
subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "torchao"], capture_output=True)

import torch
from diffusers import (
    StableDiffusionXLPipeline,
    EulerDiscreteScheduler,
    LTXImageToVideoPipeline,
)
from diffusers.utils import export_to_video, load_image

WORK_DIR = Path("/kaggle/working")
KEYFRAMES_DIR = WORK_DIR / "keyframes"
CLIPS_DIR = WORK_DIR / "clips"
KEYFRAMES_DIR.mkdir(parents=True, exist_ok=True)
CLIPS_DIR.mkdir(parents=True, exist_ok=True)

# Embedded fallback configurations (injected dynamically by trigger script)
EMBEDDED_CAST = {
  "style_prefix": "Viral 3D anthropomorphic animal animation, Pixar and Unreal Engine 5 cinematic style, hyper-realistic fur textures with expressive human-like cartoon eyes and mouth, dramatic South Indian lighting, 9:16 vertical framing",
  "characters": {
    "vellai_puli_vendhan_poor": {
      "display_name": "Vellai Puli Vendhan",
      "species": "White Tiger (Daily Worker)",
      "reference_images": [
        "/kaggle/input/cast-assets/vendhan_poor.png"
      ],
      "sdxl_base_prompt": "anthropomorphic muscular white tiger with striking black stripes and bright ice-blue eyes, noble tired face, wearing a sweat-stained faded blue checkered lungi and a worn-out grey cotton shirt with a towel over his shoulder",
      "voice_profile": {
        "tts_voice_id": "ta_IN_male_deep_warm",
        "pitch": "-6%",
        "speed": "0.98"
      }
    },
    "vellai_puli_vendhan_rich": {
      "display_name": "Vellai Puli Vendhan (CEO)",
      "species": "White Tiger (Multi-Millionaire)",
      "reference_images": [
        "/kaggle/input/cast-assets/vendhan_rich.png"
      ],
      "sdxl_base_prompt": "anthropomorphic powerful white tiger with immaculate snow-white fur, sharp black stripes, confident ice-blue eyes, wearing a tailored royal navy three-piece luxury business suit, gold watch, silk tie, billionaire CEO aura",
      "voice_profile": {
        "tts_voice_id": "ta_IN_male_deep_warm",
        "pitch": "-8%",
        "speed": "0.95"
      }
    },
    "soppana_sundari": {
      "display_name": "Soppana Sundari",
      "species": "Lioness",
      "reference_images": [
        "/kaggle/input/cast-assets/sundari_front.png"
      ],
      "sdxl_base_prompt": "anthropomorphic glamorous golden-tan female lioness with sleek fur, heavy eye makeup, arrogant arched eyebrows, wearing a flashy bright red designer silk saree with heavy gold jewelry and sunglasses",
      "voice_profile": {
        "tts_voice_id": "ta_IN_female_fiery",
        "pitch": "+8%",
        "speed": "1.08"
      }
    },
    "vengai_mavan": {
      "display_name": "Vengai Mavan",
      "species": "Black Leopard",
      "reference_images": [
        "/kaggle/input/cast-assets/vengai_front.png"
      ],
      "sdxl_base_prompt": "anthropomorphic sleek jet-black panther leopard with glossy dark fur, sinister glowing amber eyes, smug grin, wearing a flashy black leather jacket with gold chains and tinted aviator sunglasses",
      "voice_profile": {
        "tts_voice_id": "ta_IN_male_dramatic",
        "pitch": "-4%",
        "speed": "1.05"
      }
    },
    "super_subbaiah": {
      "display_name": "Super Subbaiah",
      "species": "White Tiger + Lion Hybrid Cub (Male)",
      "reference_images": [
        "/kaggle/input/cast-assets/subbaiah_cub.png"
      ],
      "sdxl_base_prompt": "adorable anthropomorphic 7-year-old male hybrid cub mixing white tiger and lion features, creamy snow-white fur with faint light-grey tiger stripes, fluffy golden-cream lion cub neck tuft and round lion ears, big innocent eyes, wearing a simple yellow t-shirt and shorts",
      "voice_profile": {
        "tts_voice_id": "ta_IN_male_fast_high",
        "pitch": "+22%",
        "speed": "1.05"
      }
    },
    "sandai_saroja": {
      "display_name": "Sandai Saroja",
      "species": "White Tiger + Lion Hybrid Cub (Female)",
      "reference_images": [
        "/kaggle/input/cast-assets/saroja_cub.png"
      ],
      "sdxl_base_prompt": "adorable anthropomorphic 9-year-old female hybrid cub mixing white tiger and lion features, creamy white fur with delicate silver-grey tiger stripes, round lion cub ears with a small red hair ribbon, fierce protective big eyes, wearing a simple green pavadai sattai",
      "voice_profile": {
        "tts_voice_id": "ta_IN_female_fiery",
        "pitch": "+20%",
        "speed": "1.10"
      }
    },
    "thanga_thamarai": {
      "display_name": "Thanga Thamarai",
      "species": "Golden Tigress",
      "reference_images": [
        "/kaggle/input/cast-assets/thamarai_front.png"
      ],
      "sdxl_base_prompt": "anthropomorphic graceful golden-orange tigress with warm gentle hazel eyes, kind humble smile, jasmine flowers (mallipoo) tucked behind her ear, wearing a dignified pastel peach handloom cotton saree with a small bindi",
      "voice_profile": {
        "tts_voice_id": "ta_IN_female_fiery",
        "pitch": "-2%",
        "speed": "0.95"
      }
    }
  }
}

EMBEDDED_MANIFEST = {
  "episode_id": "ep_001",
  "title_tamil": "வெள்ளை புலி வேந்தன் - பகுதி 1: அவமானம்!",
  "title_tanglish": "Vellai Puli Vendhan - Part 1: Avamaanam!",
  "seo_metadata": {
    "hook_text": "கூலி வேலை பார்த்த வெள்ளை புலியை அவமானப்படுத்திய மனைவி! 😢🔥",
    "caption": "Vellai Puli Vendhan worked day and night for his family, only to be humiliated in public by Soppana Sundari and Vengai Mavan... Wait for Part 2! 🔥👇",
    "hashtags": [
      "#VellaiPuliVendhan",
      "#TamilAIStory",
      "#TamilShorts",
      "#TamilReels",
      "#EmotionalStoryTamil",
      "#AIAnimationTamil",
      "#KarmaStory"
    ]
  },
  "scenes": [
    {
      "scene_number": 1,
      "duration_sec": 5,
      "character_id": "vellai_puli_vendhan_poor",
      "camera_shot": "medium close-up",
      "emotion": "warm hopeful",
      "sdxl_scene_prompt": "inside a modest dim-lit Tamil village home at dusk, happily counting crumpled rupee notes and coins in a small tin box on a wooden table",
      "ltx_motion_prompt": "He gently places coins into the tin box, looks up with a proud warm smile while speaking, soft warm lamp light flickering, slow gentle camera push-in",
      "dialogue": {
        "speaker": "Vellai Puli Vendhan",
        "listener": "Soppana Sundari",
        "tamil_text": "இந்த சில்லறை காசெல்லாம் சேர்த்து வச்சிருக்கேன்... சீக்கிரமே சொந்தமா ஒரு கடை போட்டு உங்களை ராணி மாதிரி பாத்துக்குவேன்!",
        "tanglish_subtitle": "Indha chillarai kaasellam serthu vachirukken... seekirame sondhama kadai pottu ungala rani maadhiri paathukuven!"
      },
      "sfx_cue": "soft_emotional_flute"
    },
    {
      "scene_number": 2,
      "duration_sec": 5,
      "character_id": "soppana_sundari",
      "camera_shot": "medium shot",
      "emotion": "pure disgust and arrogance",
      "sdxl_scene_prompt": "standing on a crowded South Indian village street in bright daylight with villagers blurred in background, holding a packed suitcase, glaring with pure disgust and arrogance",
      "ltx_motion_prompt": "She scoffs loudly, waves her hand dismissively in anger, flips her saree pallu dramatically while shouting, sharp handheld camera shake",
      "dialogue": {
        "speaker": "Soppana Sundari",
        "listener": "Vellai Puli Vendhan",
        "tamil_text": "போதும் உன் ஓட்ட சைக்கிள் வாழ்க்கை! கூலி வேலை பாக்குற உன்கூட என்னால் வாழ முடியாது. எனக்கு பணம் வேணும்!",
        "tanglish_subtitle": "Podhum un otta cycle vaazhkai! Kooli vela paakura unkooda ennal vaazha mudiyadhu. Enakku panam venum!"
      },
      "sfx_cue": "record_scratch"
    },
    {
      "scene_number": 3,
      "duration_sec": 5,
      "character_id": "vengai_mavan",
      "camera_shot": "low-angle heroic-villain shot",
      "emotion": "cruel mocking smirk",
      "sdxl_scene_prompt": "leaning arrogantly against a shiny red luxury sports car on a dusty village street, tossing a bundle of cash in one hand",
      "ltx_motion_prompt": "He lowers his aviator sunglasses slightly, laughs cruelly, and flicks his hand dismissively toward the camera while speaking, slow arrogant camera tilt-up",
      "dialogue": {
        "speaker": "Vengai Mavan",
        "listener": "Vellai Puli Vendhan",
        "tamil_text": "டேய் வெள்ளை புலி, உன் தகுதிக்கு இவளெல்லாம் கனவுல கூட கிடைக்க மாட்டா. ஒழுங்கா ஓரமா போடா!",
        "tanglish_subtitle": "Dei Vellai Puli, un thagudhiku ivallam kanavula kooda kidaikka maatta. Ozhunga orama poda!"
      },
      "sfx_cue": "villain_bass_drop"
    },
    {
      "scene_number": 4,
      "duration_sec": 4,
      "character_id": "super_subbaiah",
      "camera_shot": "heartbreaking close-up",
      "emotion": "crying desperate",
      "sdxl_scene_prompt": "standing barefoot on a dusty village road, tears streaming down his furry cheeks, reaching out both tiny paws pleadingly toward the street",
      "ltx_motion_prompt": "Big glistening tears roll down his face, his lower lip trembles as he reaches forward crying desperately, slow emotional zoom-in",
      "dialogue": {
        "speaker": "Super Subbaiah",
        "listener": "Soppana Sundari",
        "tamil_text": "அம்மா, எங்களை விட்டு போகாதீங்கம்மா! அப்பா ரொம்ப பாவம்மா!",
        "tanglish_subtitle": "Amma, engala vittu pogadheengamma! Appa romba paavamma!"
      },
      "sfx_cue": "sad_violin"
    },
    {
      "scene_number": 5,
      "duration_sec": 4,
      "character_id": "sandai_saroja",
      "camera_shot": "tight medium close-up",
      "emotion": "determined protective glare",
      "sdxl_scene_prompt": "standing fiercely on the dusty road with fists clenched, wiping away a tear with one arm",
      "ltx_motion_prompt": "She wipes her eye quickly, raises her chin with fiery determination, and speaks boldly with energetic hand gestures, steady dramatic focus",
      "dialogue": {
        "speaker": "Sandai Saroja",
        "listener": "Vellai Puli Vendhan",
        "tamil_text": "தம்பி அழாதடா! அப்பா, நீங்க கவலைப்படாதீங்க, நான் உங்க கூட இருக்கேன்!",
        "tanglish_subtitle": "Thambi azhadhada! Appa, neenga kavalaipadadheenga, naan unga kooda irukken!"
      },
      "sfx_cue": "dramatic_swoosh"
    },
    {
      "scene_number": 6,
      "duration_sec": 5,
      "character_id": "vellai_puli_vendhan_poor",
      "camera_shot": "tight close-up",
      "emotion": "fierce burning determination",
      "sdxl_scene_prompt": "standing alone on the dusty village road as a red sports car speeds away in a cloud of dust behind him, mud splashed on his shirt, dramatic sunset backlighting",
      "ltx_motion_prompt": "Dust swirls around him, he slowly clenches his paw into a tight fist, wipes mud off his cheek, and stares straight into the camera with intense fiery resolve, dramatic rapid zoom-in",
      "dialogue": {
        "speaker": "Vellai Puli Vendhan",
        "listener": "Audience",
        "tamil_text": "இன்னைக்கு என்னை பார்த்து சிரிச்ச அதே ஊரு... ஒரு நாள் என்னை பார்த்து அண்ணாந்து பார்க்கும்!",
        "tanglish_subtitle": "Innaiku ennai paarthu siricha adhe ooru... oru naal ennai paarthu annaandhu paarkum!"
      },
      "sfx_cue": "thunder_clap"
    }
  ]
}

# Load cast bible & episode manifest with fallback
CAST_PATH = Path("/kaggle/input/vellai-puli-cast-assets/characters.json")
if CAST_PATH.exists():
    CAST = json.loads(CAST_PATH.read_text(encoding="utf-8"))
elif Path("characters.json").exists():
    CAST = json.loads(Path("characters.json").read_text(encoding="utf-8"))
else:
    CAST = EMBEDDED_CAST

MANIFEST_PATH = Path("episode_manifest.json")
if MANIFEST_PATH.exists():
    MANIFEST = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
else:
    MANIFEST = EMBEDDED_MANIFEST


def clear_vram():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def render_keyframes():
    print("--- STAGE 1: Generating Keyframes (SDXL-Lightning 8-Step) ---", flush=True)
    pipe = StableDiffusionXLPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        torch_dtype=torch.float16,
        variant="fp16",
    ).to("cuda")

    pipe.load_lora_weights(
        "ByteDance/SDXL-Lightning",
        weight_name="sdxl_lightning_8step_lora.safetensors"
    )
    pipe.fuse_lora()
    pipe.scheduler = EulerDiscreteScheduler.from_config(
        pipe.scheduler.config, timestep_spacing="trailing"
    )

    for scene in MANIFEST["scenes"]:
        char = CAST["characters"][scene["character_id"]]

        # Front-load character + outfit + action so SDXL doesn't drop clothes/backgrounds
        full_prompt = (
            f"{char['sdxl_base_prompt']}, {scene['sdxl_scene_prompt']}, "
            f"{scene['emotion']} expression, {scene['camera_shot']}, "
            f"3D Pixar animation, cinematic South Indian lighting, vibrant colors"
        )

        print(f"Rendering Keyframe {scene['scene_number']:02d} ({char['display_name']})...", flush=True)
        image = pipe(
            prompt=full_prompt,
            negative_prompt="naked animal, plain background, snow, blurry, deformed, extra limbs, realistic documentary",
            num_inference_steps=8,
            guidance_scale=2.0,
            width=576,
            height=1024,
        ).images[0]

        out_path = KEYFRAMES_DIR / f"scene_{scene['scene_number']:02d}.png"
        image.save(out_path)
        print(f"Saved keyframe: {out_path}", flush=True)

    del pipe
    clear_vram()


def animate_clips():
    print("--- STAGE 2: Animating Keyframes (Real LTX-Video I2V) ---", flush=True)
    # T4 supports float16 natively; bfloat16 is supported on Ampere/Hopper+
    ltx_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    print(f"Loading LTX-Video with precision: {ltx_dtype}...", flush=True)

    pipe = LTXImageToVideoPipeline.from_pretrained(
        "Lightricks/LTX-Video",
        torch_dtype=ltx_dtype,
    )
    # Keeps peak VRAM safely under Kaggle T4 16GB limit
    pipe.enable_model_cpu_offload()
    pipe.vae.enable_tiling()

    for scene in MANIFEST["scenes"]:
        img_path = KEYFRAMES_DIR / f"scene_{scene['scene_number']:02d}.png"
        if not img_path.exists():
            print(f"Skipping scene_{scene['scene_number']:02d}, keyframe missing.", flush=True)
            continue

        image = load_image(str(img_path))

        # LTX requires frame count = 8k + 1 (73 frames ≈ 3s, 97 frames ≈ 4s at 24fps)
        num_frames = 97 if scene.get("duration_sec", 4) >= 5 else 73

        print(f"Generating LTX I2V clip for Scene {scene['scene_number']:02d} ({num_frames} frames)...", flush=True)
        video_frames = pipe(
            image=image,
            prompt=f"{scene['ltx_motion_prompt']}, smooth 3D Pixar character animation, expressive talking mouth movement",
            negative_prompt="static image, slideshow, zoom only, worst quality, blurry, jittery, morphing face, extra limbs",
            width=576,
            height=1024,
            num_frames=num_frames,
            num_inference_steps=20,
            guidance_scale=3.5,
        ).frames[0]

        out_mp4 = CLIPS_DIR / f"scene_{scene['scene_number']:02d}.mp4"
        export_to_video(video_frames, str(out_mp4), fps=24)
        print(f"Saved animated clip: {out_mp4}", flush=True)

    del pipe
    clear_vram()


if __name__ == "__main__":
    render_keyframes()
    animate_clips()
    print("DONE: All animated .mp4 clips saved to /kaggle/working/clips/", flush=True)
