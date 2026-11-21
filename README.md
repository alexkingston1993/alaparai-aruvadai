# 🎬 AI Videos — Autonomous Viral Tamil Web Series Pipeline

Autonomous production pipeline for generating 3D anthropomorphic comedy web series (YouTube Shorts / Instagram Reels) using free cloud hardware (**Kaggle GPU T4 x2**) and local orchestration.

---

## 🏗️ Architecture

```
[1. Local Scriptwriter]     --->     [2. Cloud GPU Renderer]     --->     [3. Local Assembler]
 OpenRouter (Llama 3.3)               Kaggle Headless Worker               Edge-TTS + FFmpeg
 outputs manifest.json                SDXL-Lightning + LTX-2.5             Tamil Voice + SFX + Subtitles
```

1. **Stage 1 (Local):** Generates episodic scripts adhering to South Indian comedy timing and character bibles (`config/characters.json`), outputting a structured scene manifest.
2. **Stage 2 (Kaggle Cloud GPU):** Headlessly generates 576x1024 starting keyframes via SDXL-Lightning 4-step, then animates motion and expressions via LTX-Video I2V with sequential offloading.
3. **Stage 3 (Local Assembly):** Synthesizes expressive Tamil speech with pitch/rate shifting, stretches/syncs video clips, mixes viral meme sound effects and BGM, burns bold Tanglish subtitles, and exports 1080x1920 vertical MP4s.

---

## 🎭 The Cast (3D Anthropomorphic Comedy)

- **Vayithaali Varkee:** Anxious crispy Ooty Varkey puff biscuit with thin moustache and floating pastry crumbs.
- **Maama Vayiru:** Giant pot-bellied watermelon with a thick handlebar moustache, lazy eyes, and lungi.
- **Rangeela Ramasaami:** Flashy golden pineapple with green leaf puff hair, retro sunglasses, and gold chain.
- **Mottai Murungakkai:** Tall skinny lecturing uncle drumstick.
- **Pattasu Pacha Milagai:** Fiery hot-tempered green chili with smoking stem.
- **Thimiru Thengai:** Stubborn cracked brown coconut.

---

## 🚀 Quickstart

### 1. Installation

```bash
git clone https://github.com/alexkingston1993/ai-videos.git
cd ai-videos
pip install -r requirements.txt
cp .env.example .env
# Fill in OPENROUTER_API_KEY and Kaggle credentials in .env or ~/.kaggle/kaggle.json
```

Make sure `ffmpeg` is installed:
```bash
brew install ffmpeg
```

### 2. Generate an Episode Manifest

```bash
python scripts/1_generate_script.py "Rangeela Ramasaami sells a fake VIP lottery ticket to Maama Vayiru" 1
```

### 3. Render on Kaggle Cloud GPU

Configure your Kaggle username in `kaggle_worker/kernel-metadata.json`, then trigger:

```bash
python scripts/2_trigger_kaggle.py
```

### 4. Assemble Final Video

```bash
python scripts/3_assemble_video.py
```
Your final compiled video will be saved in `output/ep_001_final.mp4`.

---

## 🏷️ Renaming This Repository Later

When you finalize your official YouTube channel name, rename this GitHub repository in one command:

```bash
/usr/local/bin/gh repo rename <your-new-channel-name> -y
git remote set-url origin https://github.com/alexkingston1993/<your-new-channel-name>.git
```
