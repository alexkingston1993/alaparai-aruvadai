# 🌾 அலப்பறை அறுவடை (Alaparai Aruvadai) — Autonomous Tamil AI Web Series Pipeline

[![GitHub Repo](https://img.shields.io/badge/GitHub-alaparai--aruvadai-blue?logo=github)](https://github.com/alexkingston1993/alaparai-aruvadai)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Autonomous production pipeline for generating viral 3D anthropomorphic comedy & drama web series (YouTube Shorts / Instagram Reels) in spoken Tamil, powered by **Kaggle's free GPU T4 x2** cloud worker and local Python orchestration.

---

## 🌟 Flagship Series: **வெள்ளை புலி வேந்தன் (Vellai Puli Vendhan)**

An emotional, high-stakes 4-part karma story packed with dramatic confrontation, hustle, and triumphant vengeance:

- **Episode 1: அவமானம்! (Avamaanam!)** — A poor, hardworking white tiger is publicly humiliated and abandoned by his arrogant lioness wife for a wealthy panther.
- **Episode 2: உழைப்பு & தங்க தாமரை (Ulaippu & Thanga Thamarai)** — With the faithful golden tigress caring for his children, Vendhan's relentless warehouse hustle takes off.
- **Episode 3: கோடீஸ்வரன்! (Kodeeswaran!)** — 5 years later: Vendhan buys out his rival's bankrupt empire at auction.
- **Episode 4: கர்மா & கல்யாணம்! (Karma & Kalyanam!)** — The finale: Vendhan rejects his manipulative ex and marries the gem who stood by him.

---

## 🏗️ Architecture

```
[1. Local Manifests]          --->    [2. Cloud GPU Renderer]     --->    [3. Local Assembly]
 manifests/ep_001_manifest.json        Kaggle Headless Worker              scripts/3_assemble_video.py
 (Prompts, Dialogues, SFX)             SDXL-Lightning + LTX-2.5            Edge-TTS + FFmpeg + ASS Subtitles
```

1. **Stage 1 (Story & Cast Bible):** Character profiles in `config/characters.json` define exact SDXL prompts, voice profiles, pitch/speed shifts, and reference images.
2. **Stage 2 (Cloud GPU Worker):** Headless Kaggle script (`kaggle_worker/render_episode.py`) generates 576×1024 starting keyframes (SDXL-Lightning 4-step) and animates full motion & lip gestures (LTX-Video I2V with sequential CPU offloading).
3. **Stage 3 (Video & Audio Assembly):** Generates neural Tamil voiceovers via Edge-TTS, aligns video to speech timing, mixes viral meme sound effects and BGM, and burns high-contrast Tanglish karaoke subtitles.

---

## 🚀 Quickstart

### 1. Setup

```bash
git clone https://github.com/alexkingston1993/alaparai-aruvadai.git
cd alaparai-aruvadai
pip install -r requirements.txt
```

Ensure `ffmpeg` is available on your machine:
```bash
brew install ffmpeg
```

### 2. Configure Kaggle Credentials

Add your Kaggle username to `kaggle_worker/kernel-metadata.json`:
```json
{
  "id": "YOUR_KAGGLE_USERNAME/tamil-ai-webseries-worker",
  ...
}
```

### 3. Run an Episode on Kaggle Cloud GPU

To render Episode 1 (or any episode `ep_001`–`ep_004`):
```bash
python scripts/2_trigger_kaggle.py ep_001
```

This stages the episode manifest, pushes the job to Kaggle, monitors status until complete, and downloads all rendered `.mp4` clips to `rendered_clips/ep_001/`.

### 4. Assemble Video with Voiceover & Subtitles

```bash
python scripts/3_assemble_video.py ep_001
```

The final polished 1080×1920 vertical video will be saved to:
`output/ep_001_final.mp4`

---

## 📂 Project Structure

```
alaparai-aruvadai/
├── config/
│   └── characters.json          # 3D cast definitions, voice profiles, SDXL prompts
├── manifests/
│   ├── ep_001_manifest.json     # Episode 1: Avamaanam
│   ├── ep_002_manifest.json     # Episode 2: Ulaippu & Thanga Thamarai
│   ├── ep_003_manifest.json     # Episode 3: Kodeeswaran
│   └── ep_004_manifest.json     # Episode 4: Karma & Kalyanam
├── kaggle_worker/
│   ├── render_episode.py        # Headless SDXL-Lightning + LTX-2.5 script
│   ├── kernel-metadata.json     # Kaggle GPU T4 x2 configuration
│   └── episode_manifest.json    # Currently staged episode
├── scripts/
│   ├── 1_generate_script.py     # LLM scriptwriting generator
│   ├── 2_trigger_kaggle.py      # Multi-episode Kaggle GPU pusher & puller
│   ├── 3_assemble_video.py      # Edge-TTS voice + FFmpeg assembly + ASS subtitles
│   └── 4_generate_thumbnail.py   # High-contrast cover generator
├── assets/
│   ├── sfx/                     # Meme sound effect mp3s (vine_boom, record_scratch, etc.)
│   ├── bgm/                     # Background music loops
│   └── cast_references/         # Character reference images
└── output/                      # Final assembled ready-to-publish MP4s
```
