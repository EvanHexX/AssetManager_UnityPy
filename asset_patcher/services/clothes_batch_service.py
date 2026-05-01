# asset_patcher/services/clothes_batch_service.py
# 설명:
# 여러 의상 PNG 패치 요청을 한 번에 처리한다.
# 같은 atlas 파일이 여러 번 수정되어도 마지막에 한 번만 저장한다.

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from asset_patcher.services.clothes_patch_service import ClothesPatchService


@dataclass
class ClothesBatchPatchResult:
    """
    의상 batch patch 결과.
    """

    status: str
    success_count: int
    failed_count: int
    results: list[dict[str, Any]]
    errors: list[dict[str, Any]]


class ClothesBatchPatchService:
    """
    여러 의상 패치 요청을 순차 처리하는 서비스.
    """

    def __init__(self, texture_metadata_path: str | Path) -> None:
        """
        ClothesBatchPatchService를 초기화한다.

        Args:
            texture_metadata_path: data.tsv 경로
        """

        self.service = ClothesPatchService(
            texture_metadata_path=texture_metadata_path,
        )

    def patch_many(
            self,
            jobs: list[dict[str, Any]],
            stop_on_error: bool = True,
            dry_run: bool = False,
    ) -> ClothesBatchPatchResult:
        """
        여러 의상 패치 job을 처리한다.

        Args:
            jobs: patch job 목록
            stop_on_error: 하나 실패 시 즉시 중단할지 여부
            dry_run: 실제 저장 없이 검증만 할지 여부

        Job 형식:
            {
              "request": {...},
              "assets_file": "...",
              "png_file": "...",
              "atlas_file": "...",
              "output_assets_file": null,
              "flip_y": false
            }

        Returns:
            ClothesBatchPatchResult
        """

        results: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        for index, job in enumerate(jobs):
            try:
                # ✅ 핵심: 각 job은 단일 패치 서비스로 처리한다.
                result = self.service.patch_one(
                    request_data=job["request"],
                    assets_file=job["assets_file"],
                    png_file=job["png_file"],
                    atlas_file=job.get("atlas_file"),
                    output_assets_file=job.get("output_assets_file"),
                    flip_y=bool(job.get("flip_y", False)),
                    dry_run=dry_run,
                )

                results.append(
                    {
                        "index": index,
                        "status": result.status,
                        "mode": result.mode,
                        "request": result.request,
                        "result": result.result,
                    }
                )

            except Exception as exc:
                error = {
                    "index": index,
                    "request": job.get("request"),
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }

                errors.append(error)

                if stop_on_error:
                    break

        # ✅ 모든 job 처리 후 atlas 변경사항을 한 번만 저장한다.
        # dry_run이면 저장하지 않는다.
        if not dry_run and not errors:
            self.service.save_atlas_all()

        status = "success" if not errors else "failed"

        return ClothesBatchPatchResult(
            status=status,
            success_count=len(results),
            failed_count=len(errors),
            results=results,
            errors=errors,
        )
