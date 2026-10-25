# character-card-mac

Portable **character sheet** pipeline for an **M4 Pro Mac Mini with 24 GB** unified memory.

Grok Bot designs the card (JSON). **mflux + FLUX.1-schnell (4-bit, low-ram)** renders one panel at a time. Pillow composites the sheet.

This is the Apple Silicon counterpart to [ComfyUI-CharacterCardStudio](https://github.com/JGRFW/ComfyUI-CharacterCardStudio) (Qwen-Image 2.1 inside ComfyUI). Layouts are inspired by that MIT project; the runtime is intentionally different.

> **Memory note:** If you wrote “24MB”, that is only enough for the JSON plan / tiny assets — not a diffusion model. This toolkit assumes **24 GB** (typical M4 Pro Mac Mini config).

## How Character Card Studio actually works

That ComfyUI plugin does **not** emit chatbot “character cards.” It builds a **visual multi-panel reference sheet**:

```text
character description or reference image
        ↓
template (cell positions as fractions of the canvas)
        ↓
Qwen-Image 2.1 generates each view (or one big sheet, then slice)
        ↓
Pillow re-fits panels and pastes them onto the card layout
```

Key files in the upstream plugin:

| Piece | Role |
|---|---|
| `templates.py` | Card layouts + `compile_prompt()` |
| `simple_nodes.py` | `Qwen21ModelLoader` + per-cell `CharacterCardGeneratorSingle` |
| `nodes.py` | One-click prompt compiler + sheet splitter |
| `renderer.py` / `splitter.py` | Layout guide images + crop/recompose |
| `workflows/*QwenImage21*.json` | Ready ComfyUI graphs |

Recommended upstream weights (heavy for 24 GB Apple Silicon when CLIP + UNET + VAE are resident):

- UNET `qwen_image_2.1_bf16` or `…_int8_convrot`
- CLIP `qwen3vl_8b_int8_convrot` (`qwen_image`)
- VAE `qwen_image_2.1_vae_bf16`
- Encoder node `TextEncodeQwenImage21`

On NVIDIA, INT8 Qwen-Image 2.1 often peaks around **~14–21 GB** depending on encoder residency. On a **24 GB M4 Pro**, that stack is tight once macOS + ComfyUI overhead are included. Prefer this repo’s **FLUX schnell 4-bit** path instead.

## Why FLUX/mflux here

| Goal | Choice |
|---|---|
| Fit ~24 GB unified memory | `mflux-generate --model schnell --quantize 4 --low-ram` |
| Keep peak RAM down | **One cell per run**, then compose (same idea as `CharacterCardGeneratorSingle`) |
| Avoid Qwen3-VL encoder tax | FLUX text encoders + low-ram release after encode |
| Still get a “character card” | Same template → cells → compose pattern |

## Install

```bash
cd character_card_mac
python -m venv .venv && source .venv/bin/activate
pip install -e .

# On the Mac Mini only, for real images:
pip install 'mflux>=0.13.0'
```

## Venice AI (chat / card design)

Venice is OpenAI-compatible ([docs](https://docs.venice.ai)). Copy the repo-root `.env.example` to `.env` and set `VENICE_API_KEY` (never commit `.env`).

```bash
# from repo root
cp .env.example .env   # then edit VENICE_API_KEY=

python character_card_mac/scripts/venice_smoke.py
# or:
character-card-mac venice-chat --prompt "Reply with exactly: venice-ok"
```

Defaults: `https://api.venice.ai/api/v1`, model `zai-org-glm-5-2`.

## Grok Bot → plan → sheet

1. Give Grok the system prompt in [`prompts/grok_system.md`](prompts/grok_system.md).
2. Ask for a character. Grok returns JSON (see [`examples/sample_character.json`](examples/sample_character.json)).
3. On the Mac:

```bash
# Build a full plan (layout + engine hints) from Grok's fields
character-card-mac design \
  --title "Mira Vale" \
  --identity "A 28-year-old cartographer..." \
  --appearance "Sharp oval face, olive skin, black bob..." \
  --outfit "Olive field jacket, cream turtleneck..." \
  --palette "olive, cream, charcoal, brass" \
  --template turnaround_6 \
  --overrides examples/sample_character.json \
  --out /tmp/mira_plan.json

# Dry run anywhere (colored placeholders — no GPU)
character-card-mac generate --plan /tmp/mira_plan.json --backend placeholder --out /tmp/mira_out

# Real generation on Apple Silicon
character-card-mac generate --plan /tmp/mira_plan.json --backend mflux --out ~/Sheets/mira
```

Inspect compiled FLUX prompts without generating:

```bash
character-card-mac prompts --plan /tmp/mira_plan.json
```

## CLI

```bash
character-card-mac templates
character-card-mac design --help
character-card-mac prompts --plan plan.json
character-card-mac generate --plan plan.json --backend placeholder|mflux --out ./out
```

## Smoke test (no Mac required)

```bash
python scripts/smoke_test.py
```

## Mapping to the ComfyUI plugin

| CharacterCardStudio | This toolkit |
|---|---|
| `AICG3D_CardSettingsFive` / OneClick | `character-card-mac design` + Grok JSON |
| `AICG3D_Qwen21ModelLoader` | mflux FLUX.1-schnell 4-bit |
| `TextEncodeQwenImage21` | FLUX prompt string from `prompts.py` |
| `AICG3D_CharacterCardGeneratorSingle` | `generate.py` loop (one cell → PNG) |
| Asset composer / splitter | `compose.py` |

## License

MIT. Layout concept adapted from ComfyUI-CharacterCardStudio (MIT).
