#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke test: design → prompts → placeholder compose (no Apple Silicon required)."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from character_card_mac.design import build_card_plan, merge_grok_overrides, save_plan
from character_card_mac.generate import generate_sheet
from character_card_mac.prompts import compile_all_cell_prompts


def main() -> int:
    overrides = json.loads((ROOT / "examples" / "sample_character.json").read_text(encoding="utf-8"))
    plan = build_card_plan(
        title=overrides["title"],
        identity=overrides["identity"],
        appearance=overrides["appearance"],
        outfit=overrides.get("outfit", ""),
        palette=overrides.get("palette", ""),
        style=overrides.get("style"),
        template_id=overrides.get("templateId", "turnaround_6"),
        memory_budget_gb=24.0,
    )
    plan = merge_grok_overrides(plan, overrides)
    prompts = compile_all_cell_prompts(plan)
    assert len(prompts) == 6, prompts

    with tempfile.TemporaryDirectory() as tmp:
        plan_path = save_plan(plan, Path(tmp) / "plan.json")
        paths = generate_sheet(plan, Path(tmp) / "out", backend="placeholder", seed=7)
        assert paths["sheet"].exists()
        assert paths["report"].exists()
        print("ok", plan_path.name, paths["sheet"], f"cells={len(prompts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
