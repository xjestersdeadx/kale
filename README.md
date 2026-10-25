# kale

Toolkit experiments.

## Setup

```bash
cp .env.example .env
# set VENICE_API_KEY=...  (.env is gitignored)
```

Venice AI is OpenAI-compatible at `https://api.venice.ai/api/v1` (model `zai-org-glm-5-2`). See [`character_card_mac/README.md`](character_card_mac/README.md).

## character-card-mac

Apple Silicon character-sheet generator: **Grok/Venice designs the card → mflux/FLUX renders panels → Pillow composes the sheet**.

See [`character_card_mac/README.md`](character_card_mac/README.md).

Built as a 24 GB M4 Pro–friendly alternative to [ComfyUI-CharacterCardStudio](https://github.com/JGRFW/ComfyUI-CharacterCardStudio)’s Qwen-Image 2.1 ComfyUI pipeline.
