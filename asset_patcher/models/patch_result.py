# asset_patcher/models/patch_result.py

from dataclasses import dataclass
from typing import Any


@dataclass
class BasePatchResult:
    status: str
    message: str | None = None


@dataclass
class ClothesPatchResult(BasePatchResult):
    mode: str
    request: dict[str, Any]
    result: dict[str, Any]


@dataclass
class BatchPatchResult(BasePatchResult):
    success_count: int
    failed_count: int
    results: list[dict[str, Any]]
    errors: list[dict[str, Any]]