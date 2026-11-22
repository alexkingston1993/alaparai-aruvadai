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

## 🏗️ Architecture & Isolation

```
[1. Local Manifests]          --->    [2. Isolated Cloud GPU]     --->    [3. Local Assembly]
 manifests/ep_001_manifest.json        alexytcreative/                     scripts/3_assemble_video.py
 (Prompts, Dialogues, SFX)             vellai-puli-vendhan-worker          Edge-TTS + FFmpeg + Pillow Subtitles
                                       SDXL-Lightning + LTX-2.5 I2V
```

### 🔒 Project & Quota Isolation

- **Dedicated Kernel Slug:** Uses `alexytcreative/vellai-puli-vendhan-worker` so packages, scripts, and output files never collide with other Kaggle projects.
- **Shared Account Limits:** Kaggle free tier allocates 30 GPU hours/week across all kernels. Run episodes when other project GPU sessions are idle.
- **Real LTX-Video I2V:** Stage 2 executes `LTXImageToVideoPipeline` (20-step distilled I2V) with sequential CPU offload and float16 precision optimized for Tesla T4 GPUs.

---

## 🚀 Quickstart

### 1. Setup

```bash
git clone https://github.com/alexkingston1993/alaparai-aruvadai.git
cd alaparai-aruvadai
pip install -r requirements.txt
```

### 2. Render on Kaggle Cloud GPU

To render Episode 1 (or any episode `ep_001`–`ep_004`):
```bash
python3 scripts/2_trigger_kaggle.py ep_001
```

This stages the episode manifest, pushes the dedicated worker kernel to Kaggle, monitors status until complete, and downloads all rendered `.mp4` clips to `rendered_clips/ep_001/`.

### 3. Assemble Video with Voiceover & Subtitles

The trigger script automatically calls assembly upon downloading clips, or you can run it manually:
```bash
python3 scripts/3_assemble_video.py ep_001
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
│   ├── render_episode.py        # Headless SDXL-Lightning 8-step + LTX-Video I2V script
│   ├── kernel-metadata.json     # Isolated worker ID: alexytcreative/vellai-puli-vendhan-worker
│   └── episode_manifest.json    # Currently staged episode
├── scripts/
│   ├── 1_generate_script.py     # LLM scriptwriting generator
│   ├── 2_trigger_kaggle.py      # Isolated Kaggle GPU pusher & puller
│   ├── 3_assemble_video.py      # Edge-TTS voice + FFmpeg assembly + Pillow subtitles
│   └── 4_generate_thumbnail.py   # High-contrast cover generator
├── assets/
│   ├── sfx/                     # Meme sound effect mp3s (vine_boom, record_scratch, etc.)
│   ├── bgm/                     # Background music loops
│   └── cast_references/         # Character reference images
└── output/                      # Final assembled ready-to-publish MP4s
```
