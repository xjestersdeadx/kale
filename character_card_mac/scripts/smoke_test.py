#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke test: design → prompts → placeholder compose (no Apple Silicon required)."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from character_card_mac.design import build_card_plan, merge_grok_overrides, save_plan
from character_card_mac.from_image import attach_reference, create_sheet_from_image
from character_card_mac.generate import generate_sheet
from character_card_mac.prompts import compile_all_cell_prompts


def _fake_portrait(path: Path) -> None:
    img = Image.new("RGB", (512, 640), (180, 140, 110))
    draw = ImageDraw.Draw(img)
    draw.ellipse((156, 80, 356, 280), fill=(220, 180, 150))
    draw.rectangle((190, 300, 322, 560), fill=(60, 90, 70))
    img.save(path)


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
        tmp_path = Path(tmp)
        plan_path = save_plan(plan, tmp_path / "plan.json")
        paths = generate_sheet(plan, tmp_path / "out", backend="placeholder", seed=7)
        assert paths["sheet"].exists()
        assert paths["report"].exists()

        ref = tmp_path / "ref.png"
        _fake_portrait(ref)
        ref_plan = attach_reference(plan, ref, image_strength=0.5)
        assert "referenceImage" in ref_plan
        ref_paths = generate_sheet(
            ref_plan,
            tmp_path / "out_ref",
            backend="placeholder",
            seed=7,
            reference_image=ref,
        )
        assert ref_paths["sheet"].exists()
        report = json.loads(ref_paths["report"].read_text(encoding="utf-8"))
        assert report.get("referenceImage")

        one_shot = create_sheet_from_image(
            ref,
            tmp_path / "from_image",
            title="Smoke Ref",
            backend="placeholder",
            describe=False,
            image_strength=0.5,
        )
        assert one_shot["sheet"].exists()
        assert one_shot["plan"].exists()
        saved = json.loads(one_shot["plan"].read_text(encoding="utf-8"))
        assert saved.get("referenceImage")
        assert "init/reference photo is the identity anchor" in compile_all_cell_prompts(saved)[0]["prompt"]

        print(
            "ok",
            plan_path.name,
            paths["sheet"],
            ref_paths["sheet"],
            one_shot["sheet"],
            f"cells={len(prompts)}",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
