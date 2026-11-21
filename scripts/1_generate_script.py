import json
import os
import sys
from pathlib import Path
from openai import OpenAI

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
CHARACTERS_PATH = BASE_DIR / "config" / "characters.json"
MANIFEST_OUT = BASE_DIR / "kaggle_worker" / "episode_manifest.json"

def get_client() -> OpenAI:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY environment variable not set.")
        print("Set it via: export OPENROUTER_API_KEY='your-key'")
        sys.exit(1)
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

def generate_episode(episode_num: int, topic: str, model: str = "meta-llama/llama-3.3-70b-instruct:free"):
    client = get_client()

    with open(CHARACTERS_PATH, "r", encoding="utf-8") as f:
        cast_data = json.load(f)

    cast_summary = {
        k: {
            "name": v["display_name"],
            "object": v["object_type"],
            "catchphrase": v.get("catchphrase", "")
        }
        for k, v in cast_data["characters"].items()
    }

    system_prompt = f"""
You are an expert Tamil comedy web series writer and viral video director (similar to viral Tamil comedy shorts like Thaluku Buluku Thakkali).
Write a fast-paced 30-40 second vertical comedy episode (YouTube Shorts / Instagram Reels) featuring anthropomorphic 3D food/object characters.

AVAILABLE CAST:
{json.dumps(cast_summary, indent=2)}

CRITICAL WRITING RULES:
1. Natural spoken Tamil Nadu slang ONLY (Madras/Coimbatore/Madurai local conversational tone). NO bookish/literary Tamil. NO narrator voice.
2. Hook within the first 1.5 seconds! Scene 1 MUST start in media res with high emotion (argument, shock, or absurd accusation).
3. Generate 6 to 8 rapid scenes (3-5 seconds each). Focus on ONE primary speaking character per scene (shot-reverse-shot editing).
4. `sdxl_scene_prompt`: Static starting pose, props, facial expression, and South Indian background setting in English.
5. `ltx_motion_prompt`: Detailed physical motion, animated facial movement, lip-sync energy, camera motion (e.g. dramatic push-in, handheld shake) in English.
6. `tanglish_subtitle`: Clean, easy-to-read English transliteration of the Tamil dialogue for viral on-screen captions.
7. Incorporate at least one character catchphrase naturally.

Output ONLY a single valid JSON object strictly matching this schema:
{{
  "episode_id": "ep_{episode_num:03d}",
  "title_tamil": "...",
  "title_tanglish": "...",
  "seo_metadata": {{
    "hook_text": "Shocking punchline or hook for top-banner display",
    "caption": "Short viral social caption in Tamil + Tanglish",
    "hashtags": ["#TamilComedy", "#TamilMemes", "#AIAnimation", "#ReelsTamil"]
  }},
  "scenes": [
    {{
      "scene_number": 1,
      "duration_sec": 4,
      "character_id": "rangeela_ramasaami",
      "camera_shot": "close-up",
      "emotion": "cocky smirk",
      "sdxl_scene_prompt": "Rangeela Ramasaami standing in a crowded Chennai tea stall holding a fake golden lottery ticket, squinting smugly",
      "ltx_motion_prompt": "He winks cockily, tilts his pineapple head forward, and laughs boastfully while waving the golden ticket towards camera",
      "dialogue": {{
        "speaker": "Rangeela Ramasaami",
        "listener": "Maama Vayiru",
        "tamil_text": "டேய் மாமா வயிறு! இந்த லாட்டரி அடிச்சதுக்கு அப்புறம் உன் வயித்த பாக்கவே மாட்டேன் டா!",
        "tanglish_subtitle": "Dey Maama Vayiru! Indha lottery adichadhum un vayitha paakkave maatten da!"
      }},
      "sfx_cue": "vine_boom"
    }}
  ]
}}
"""

    print(f"Generating Episode {episode_num} on topic: '{topic}' using model: {model}...")
    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f'Write Episode {episode_num} on the topic: "{topic}"'},
        ],
        temperature=0.8,
    )

    content = response.choices[0].message.content
    manifest = json.loads(content)

    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_OUT, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"SUCCESS: Generated {len(manifest['scenes'])} scenes.")
    print(f"Saved manifest to: {MANIFEST_OUT}")
    return manifest

if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else "Rangeela Ramasaami sells a 100-crore fake tea-cup lottery ticket to Maama Vayiru at a busy local tea kadai"
    ep_num = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    generate_episode(ep_num, topic)
