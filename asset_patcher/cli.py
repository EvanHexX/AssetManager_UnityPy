# asset_patcher/cli.py
# 설명:
# - patch_plan.json을 받아 task를 순차 실행합니다.
# - 현재는 texture_ress_patch만 실제 구현되어 있습니다.

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from asset_patcher.plan_loader import load_patch_plan
from asset_patcher.modules.texture_ress_patch import run_texture_ress_patch
from asset_patcher.core.backup import restore_backup

def main() -> int:
    parser = argparse.ArgumentParser(prog="AssetManager_UnityPy")
    parser.add_argument("--plan", required=True, help="patch_plan.json path")
    parser.add_argument("--restore-latest", action="store_true", help="latest backup restore")
    parser.add_argument("--restore-stamp", help="specific backup timestamp folder name")
    args = parser.parse_args()

    plan = load_patch_plan(args.plan)
    game = plan.get("game", {})
    options = plan.get("options", {})

    game_id = game.get("id", "unknown")
    data_dir = game.get("dataDir")
    backup_dir = options.get("backupDir")

    if args.restore_latest or args.restore_stamp:
        if not backup_dir:
            raise ValueError("backupDir is required for restore")
        if not data_dir:
            raise ValueError("game.dataDir is required for restore")

        restored = restore_backup(
            backup_dir=backup_dir,
            game_id=game_id,
            data_dir=data_dir,
            backup_stamp=args.restore_stamp
        )

        print("[RESTORE] restored files:")
        for path in restored:
            print(" -", path)

        return 0
    options["_gameId"] = game_id
    stop_on_error = bool(options.get("stopOnError", True))

    results: List[Dict[str, Any]] = []

    for task in plan["tasks"]:
        if not task.get("enabled", True):
            results.append({
                "taskId": task.get("id"),
                "status": "skipped"
            })
            continue

        try:
            result = run_task(task, options)
            results.append(result)
            print("[OK]", task["id"], result.get("status"))
        except Exception as ex:
            error_result = {
                "taskId": task.get("id"),
                "status": "error",
                "error": str(ex)
            }
            results.append(error_result)
            print("[ERROR]", task.get("id"), str(ex), file=sys.stderr)

            if stop_on_error:
                break

    if options.get("writeReport", True):
        output_dir = Path(options.get("outputDir") or ".").resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        report_path = output_dir / "patch_report.json"
        with report_path.open("w", encoding="utf-8") as f:
            json.dump({
                "planName": plan.get("planName"),
                "results": results
            }, f, ensure_ascii=False, indent=2)

        print("[REPORT]", report_path)

    has_error = any(r.get("status") == "error" for r in results)
    return 1 if has_error else 0


def run_task(task: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
    task_type = task["type"]

    if task_type == "texture_ress_patch":
        return run_texture_ress_patch(task, options)

    if task_type == "atlas_text_patch":
        raise NotImplementedError("atlas_text_patch is not implemented yet")

    if task_type == "font_patch":
        # 참고:
        # 마스터 확인사항에 따라 font_patch는 resources.assets 자체 수정 계열로 설계한다.
        # texture_ress_patch처럼 .resS only 방식으로 고정하지 않는다.
        raise NotImplementedError("font_patch is not implemented yet")

    raise ValueError(f"Unsupported task type: {task_type}")


if __name__ == "__main__":
    raise SystemExit(main())