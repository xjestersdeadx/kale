# -*- coding: utf-8 -*-
"""CLI: design a character sheet plan, then generate/compose it."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .design import build_card_plan, load_plan, merge_grok_overrides, save_plan
from .generate import generate_sheet
from .prompts import compile_all_cell_prompts
from .templates import TEMPLATE_OPTIONS, list_templates
from .venice import chat_text, get_venice_settings


def _cmd_templates(_: argparse.Namespace) -> int:
    for item in list_templates():
        print(f"{item['id']:16}  {item['name']} — {item['description']}")
    return 0


def _cmd_design(args: argparse.Namespace) -> int:
    plan = build_card_plan(
        title=args.title,
        identity=args.identity,
        appearance=args.appearance,
        outfit=args.outfit or "",
        palette=args.palette or "",
        style=args.style,
        template_id=args.template,
        show_labels=args.show_labels,
        memory_budget_gb=args.memory_gb,
    )
    if args.overrides:
        overrides = json.loads(Path(args.overrides).read_text(encoding="utf-8"))
        plan = merge_grok_overrides(plan, overrides)
    path = save_plan(plan, args.out)
    print(path)
    return 0


def _cmd_prompts(args: argparse.Namespace) -> int:
    plan = load_plan(args.plan)
    rows = compile_all_cell_prompts(plan)
    text = json.dumps(rows, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(args.out)
    else:
        print(text)
    return 0


def _cmd_generate(args: argparse.Namespace) -> int:
    plan = load_plan(args.plan)
    paths = generate_sheet(
        plan,
        args.out,
        backend=args.backend,
        seed=args.seed,
        steps=args.steps,
        quantize=args.quantize,
        model=args.model,
        low_ram=not args.no_low_ram,
        fit_mode=args.fit_mode,
    )
    for key, value in paths.items():
        print(f"{key}: {value}")
    return 0


def _cmd_venice_chat(args: argparse.Namespace) -> int:
    settings = get_venice_settings()
    reply = chat_text(args.prompt, model=args.model)
    print(f"model: {args.model or settings['model']}")
    print(f"base_url: {settings['base_url']}")
    print(reply)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="character-card-mac",
        description="Design and generate Apple Silicon character sheets (Grok plan → mflux cells → compose).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_templates = sub.add_parser("templates", help="List built-in sheet layouts")
    p_templates.set_defaults(func=_cmd_templates)

    p_design = sub.add_parser("design", help="Create a Grok-compatible card plan JSON")
    p_design.add_argument("--title", required=True)
    p_design.add_argument("--identity", required=True, help="Who the character is")
    p_design.add_argument("--appearance", required=True, help="Face, hair, body lock")
    p_design.add_argument("--outfit", default="")
    p_design.add_argument("--palette", default="")
    p_design.add_argument("--style", default=None)
    p_design.add_argument("--template", default="turnaround_6", choices=[t.split(" |", 1)[0] for t in TEMPLATE_OPTIONS])
    p_design.add_argument("--show-labels", action="store_true")
    p_design.add_argument("--memory-gb", type=float, default=24.0)
    p_design.add_argument("--overrides", help="Optional JSON overrides from Grok")
    p_design.add_argument("--out", required=True)
    p_design.set_defaults(func=_cmd_design)

    p_prompts = sub.add_parser("prompts", help="Compile FLUX-ready per-cell prompts from a plan")
    p_prompts.add_argument("--plan", required=True)
    p_prompts.add_argument("--out")
    p_prompts.set_defaults(func=_cmd_prompts)

    p_gen = sub.add_parser("generate", help="Generate cells and compose the sheet")
    p_gen.add_argument("--plan", required=True)
    p_gen.add_argument("--out", required=True)
    p_gen.add_argument("--backend", choices=["placeholder", "mflux"], default="placeholder")
    p_gen.add_argument("--seed", type=int, default=42)
    p_gen.add_argument("--steps", type=int, default=2)
    p_gen.add_argument("--quantize", type=int, default=4, choices=[4, 8])
    p_gen.add_argument("--model", default="schnell")
    p_gen.add_argument("--no-low-ram", action="store_true")
    p_gen.add_argument("--fit-mode", choices=["contain", "cover"], default="contain")
    p_gen.set_defaults(func=_cmd_generate)

    p_venice = sub.add_parser("venice-chat", help="Smoke-test Venice /chat/completions")
    p_venice.add_argument(
        "--prompt",
        default="Reply with exactly: venice-ok",
        help="User message to send",
    )
    p_venice.add_argument(
        "--model",
        default=None,
        help="Model id (default: VENICE_MODEL or zai-org-glm-5-2)",
    )
    p_venice.set_defaults(func=_cmd_venice_chat)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
