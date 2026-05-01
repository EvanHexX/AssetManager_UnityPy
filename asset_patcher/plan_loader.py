# asset_patcher/plan_loader.py
# 설명:
# - patch_plan.json을 읽고 기본 구조를 검증합니다.
# - jsonschema는 선택 의존성으로 두고, 없으면 최소 검증만 수행합니다.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def load_patch_plan(plan_path: str | Path) -> Dict[str, Any]:
    path = Path(plan_path).resolve()

    if not path.exists():
        raise FileNotFoundError(f"Patch plan not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        plan = json.load(f)

    validate_minimum_plan(plan)
    return plan


def validate_minimum_plan(plan: Dict[str, Any]) -> None:
    required = ["schemaVersion", "game", "options", "tasks"]

    for key in required:
        if key not in plan:
            raise ValueError(f"Missing required key in patch plan: {key}")

    if not isinstance(plan["tasks"], list):
        raise TypeError("patch plan 'tasks' must be a list")

    for index, task in enumerate(plan["tasks"]):
        for key in ["id", "enabled", "type"]:
            if key not in task:
                raise ValueError(f"Task[{index}] missing required key: {key}")
