# asset_patcher/cli.py
# 설명:
# patch_plan.json을 입력받아 의상 PNG patch, Font patch, Font 원본 추출/복원을 실행하는 CLI 진입점.
# Electron exe 연동 전, PowerShell에서 직접 검증하기 위한 실행 파일이다.

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from asset_patcher.core.font_metadata import FontMetadataStore
from asset_patcher.core.original_store import OriginalStore
from asset_patcher.modules.font_patch import FontPatcher
from asset_patcher.services.clothes_batch_service import ClothesBatchPatchService


def load_json(path: str | Path) -> dict[str, Any]:
    """
    JSON 파일을 로드한다.

    Args:
        path: JSON 파일 경로

    Returns:
        JSON dict
    """

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"JSON 파일이 없습니다: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    """
    JSON 파일을 저장한다.

    Args:
        path: 저장할 JSON 파일 경로
        data: 저장할 데이터

    Side Effects:
        지정 경로에 JSON 파일을 생성하거나 덮어쓴다.
    """

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def resolve_path(base_dir: Path, value: str | None) -> str | None:
    """
    상대 경로를 plan 파일 기준 절대 경로로 변환한다.

    Args:
        base_dir: plan 파일이 있는 폴더
        value: 경로 문자열

    Returns:
        절대 경로 문자열 또는 None
    """

    if value is None:
        return None

    path = Path(value)

    if path.is_absolute():
        return str(path)

    return str((base_dir / path).resolve())


def normalize_clothes_jobs(plan: dict[str, Any], plan_dir: Path) -> list[dict[str, Any]]:
    """
    clothes patch jobs 경로를 정규화한다.

    Args:
        plan: patch plan dict
        plan_dir: patch plan 파일이 위치한 폴더

    Returns:
        정규화된 clothes job 목록
    """

    jobs = plan.get("jobs")

    if not isinstance(jobs, list):
        raise ValueError("clothes plan에는 jobs 배열이 필요합니다.")

    normalized: list[dict[str, Any]] = []

    for index, job in enumerate(jobs):
        if "request" not in job:
            raise ValueError(f"job[{index}]에 request가 없습니다.")

        if "assets_file" not in job:
            raise ValueError(f"job[{index}]에 assets_file이 없습니다.")

        if "png_file" not in job:
            raise ValueError(f"job[{index}]에 png_file이 없습니다.")

        normalized.append(
            {
                "request": job["request"],
                "assets_file": resolve_path(plan_dir, job["assets_file"]),
                "png_file": resolve_path(plan_dir, job["png_file"]),
                "atlas_file": resolve_path(plan_dir, job.get("atlas_file")),
                "output_assets_file": resolve_path(plan_dir, job.get("output_assets_file")),
                "flip_y": bool(job.get("flip_y", False)),
            }
        )

    return normalized


def run_clothes_plan(plan: dict[str, Any], plan_dir: Path) -> dict[str, Any]:
    """
    의상 PNG patch plan을 실행한다.

    Args:
        plan: patch plan dict
        plan_dir: plan 기준 폴더

    Returns:
        실행 결과 dict
    """

    texture_metadata_path = plan.get("texture_metadata_path")

    if not texture_metadata_path:
        raise ValueError("clothes plan에는 texture_metadata_path가 필요합니다.")

    texture_metadata_path = resolve_path(plan_dir, texture_metadata_path)

    dry_run = bool(plan.get("dry_run", False))
    stop_on_error = bool(plan.get("stop_on_error", True))

    jobs = normalize_clothes_jobs(plan, plan_dir)

    service = ClothesBatchPatchService(
        texture_metadata_path=texture_metadata_path,
    )

    result = service.patch_many(
        jobs=jobs,
        stop_on_error=stop_on_error,
        dry_run=dry_run,
    )

    return {
        "kind": "clothes",
        "status": result.status,
        "dry_run": dry_run,
        "stop_on_error": stop_on_error,
        "success_count": result.success_count,
        "failed_count": result.failed_count,
        "results": result.results,
        "errors": result.errors,
    }


def build_font_patcher(plan: dict[str, Any], plan_dir: Path) -> FontPatcher:
    """
    FontPatcher를 생성한다.

    Args:
        plan: patch plan dict
        plan_dir: plan 기준 폴더

    Returns:
        FontPatcher
    """

    font_metadata_path = plan.get("font_metadata_path")
    originals_dir = plan.get("originals_dir")

    if not font_metadata_path:
        raise ValueError("font plan에는 font_metadata_path가 필요합니다.")

    if not originals_dir:
        raise ValueError("font plan에는 originals_dir가 필요합니다.")

    return FontPatcher(
        font_metadata_store=FontMetadataStore(resolve_path(plan_dir, font_metadata_path)),
        original_store=OriginalStore(resolve_path(plan_dir, originals_dir)),
    )


def run_font_extract_plan(plan: dict[str, Any], plan_dir: Path) -> dict[str, Any]:
    """
    resources.assets에서 원본 Font 데이터를 추출한다.

    Args:
        plan: patch plan dict
        plan_dir: plan 기준 폴더

    Returns:
        실행 결과 dict
    """

    game_id = plan.get("game_id")
    assets_file = plan.get("assets_file")

    if not game_id:
        raise ValueError("font_extract plan에는 game_id가 필요합니다.")

    if not assets_file:
        raise ValueError("font_extract plan에는 assets_file이 필요합니다.")

    overwrite = bool(plan.get("overwrite", False))

    patcher = build_font_patcher(plan, plan_dir)

    results = patcher.extract_originals(
        game_id=game_id,
        assets_file=resolve_path(plan_dir, assets_file),
        overwrite=overwrite,
    )

    return {
        "kind": "font_extract",
        "status": "success",
        "game_id": game_id,
        "overwrite": overwrite,
        "results": results,
    }


def run_font_patch_plan(plan: dict[str, Any], plan_dir: Path) -> dict[str, Any]:
    """
    resources.assets 내부 Font 데이터를 교체한다.

    Args:
        plan: patch plan dict
        plan_dir: plan 기준 폴더

    Returns:
        실행 결과 dict
    """

    game_id = plan.get("game_id")
    assets_file = plan.get("assets_file")
    jobs = plan.get("jobs")
    dry_run = bool(plan.get("dry_run", False))
    stop_on_error = bool(plan.get("stop_on_error", True))

    if not game_id:
        raise ValueError("font plan에는 game_id가 필요합니다.")

    if not assets_file:
        raise ValueError("font plan에는 assets_file이 필요합니다.")

    if not isinstance(jobs, list):
        raise ValueError("font plan에는 jobs 배열이 필요합니다.")

    patcher = build_font_patcher(plan, plan_dir)

    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for index, job in enumerate(jobs):
        try:
            replacement_font_file = job.get("replacement_font_file")

            if not replacement_font_file:
                raise ValueError(f"font job[{index}]에 replacement_font_file이 없습니다.")

            output_file = job.get("output_file", plan.get("output_file"))

            # ✅ 우선순위:
            # 1. path_id가 있으면 path_id 기준
            # 2. 없으면 font_name 기준
            if "path_id" in job:
                result = patcher.patch_by_path_id(
                    game_id=game_id,
                    path_id=int(job["path_id"]),
                    assets_file=resolve_path(plan_dir, assets_file),
                    replacement_font_file=resolve_path(plan_dir, replacement_font_file),
                    output_file=resolve_path(plan_dir, output_file),
                    dry_run=dry_run,
                )
            elif "font_name" in job:
                result = patcher.patch_by_name(
                    game_id=game_id,
                    font_name=str(job["font_name"]),
                    assets_file=resolve_path(plan_dir, assets_file),
                    replacement_font_file=resolve_path(plan_dir, replacement_font_file),
                    output_file=resolve_path(plan_dir, output_file),
                    dry_run=dry_run,
                )
            else:
                raise ValueError(f"font job[{index}]에는 path_id 또는 font_name이 필요합니다.")

            results.append(
                {
                    "index": index,
                    "status": result.status,
                    "result": asdict(result),
                }
            )

        except Exception as exc:
            errors.append(
                {
                    "index": index,
                    "job": job,
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
            )

            if stop_on_error:
                break

    return {
        "kind": "font",
        "status": "success" if not errors else "failed",
        "dry_run": dry_run,
        "stop_on_error": stop_on_error,
        "success_count": len(results),
        "failed_count": len(errors),
        "results": results,
        "errors": errors,
    }


def run_font_restore_plan(plan: dict[str, Any], plan_dir: Path) -> dict[str, Any]:
    """
    originals에 저장된 원본 Font 데이터로 resources.assets를 복원한다.

    Args:
        plan: patch plan dict
        plan_dir: plan 기준 폴더

    Returns:
        실행 결과 dict
    """

    game_id = plan.get("game_id")
    assets_file = plan.get("assets_file")
    jobs = plan.get("jobs")
    dry_run = bool(plan.get("dry_run", False))
    stop_on_error = bool(plan.get("stop_on_error", True))

    if not game_id:
        raise ValueError("font_restore plan에는 game_id가 필요합니다.")

    if not assets_file:
        raise ValueError("font_restore plan에는 assets_file이 필요합니다.")

    if not isinstance(jobs, list):
        raise ValueError("font_restore plan에는 jobs 배열이 필요합니다.")

    patcher = build_font_patcher(plan, plan_dir)

    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for index, job in enumerate(jobs):
        try:
            if "path_id" not in job:
                raise ValueError(f"font_restore job[{index}]에는 path_id가 필요합니다.")

            output_file = job.get("output_file", plan.get("output_file"))

            result = patcher.restore_by_path_id(
                game_id=game_id,
                path_id=int(job["path_id"]),
                assets_file=resolve_path(plan_dir, assets_file),
                output_file=resolve_path(plan_dir, output_file),
                dry_run=dry_run,
            )

            results.append(
                {
                    "index": index,
                    "status": result.status,
                    "result": asdict(result),
                }
            )

        except Exception as exc:
            errors.append(
                {
                    "index": index,
                    "job": job,
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
            )

            if stop_on_error:
                break

    return {
        "kind": "font_restore",
        "status": "success" if not errors else "failed",
        "dry_run": dry_run,
        "stop_on_error": stop_on_error,
        "success_count": len(results),
        "failed_count": len(errors),
        "results": results,
        "errors": errors,
    }


def run_plan(plan_path: str | Path) -> dict[str, Any]:
    """
    patch_plan.json을 실행한다.

    Args:
        plan_path: patch_plan.json 경로

    Returns:
        실행 결과 dict
    """

    plan_path = Path(plan_path).resolve()
    plan_dir = plan_path.parent

    plan = load_json(plan_path)
    kind = plan.get("kind", "clothes")

    if kind == "clothes":
        return run_clothes_plan(plan, plan_dir)

    if kind == "font_extract":
        return run_font_extract_plan(plan, plan_dir)

    if kind == "font":
        return run_font_patch_plan(plan, plan_dir)

    if kind == "font_restore":
        return run_font_restore_plan(plan, plan_dir)

    raise ValueError(f"지원하지 않는 plan kind입니다: {kind}")


def build_parser() -> argparse.ArgumentParser:
    """
    CLI argument parser를 생성한다.

    Returns:
        argparse.ArgumentParser
    """

    parser = argparse.ArgumentParser(
        prog="asset-patcher",
        description="Unity asset patch CLI",
    )

    parser.add_argument(
        "--plan",
        required=True,
        help="patch_plan.json 경로",
    )

    parser.add_argument(
        "--report",
        default=None,
        help="patch 결과 report JSON 저장 경로",
    )

    return parser


def main() -> int:
    """
    CLI main 함수.

    Returns:
        process exit code
    """

    parser = build_parser()
    args = parser.parse_args()

    try:
        result = run_plan(args.plan)

        print(json.dumps(result, ensure_ascii=False, indent=2))

        if args.report:
            write_json(args.report, result)

        return 0 if result["status"] == "success" else 1

    except Exception as exc:
        error_result = {
            "status": "error",
            "error_type": type(exc).__name__,
            "message": str(exc),
        }

        print(json.dumps(error_result, ensure_ascii=False, indent=2), file=sys.stderr)

        if args.report:
            write_json(args.report, error_result)

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
