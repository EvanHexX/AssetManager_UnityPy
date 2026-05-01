# asset_patcher/core/backup.py
# 설명:
# - 패치 전 원본 파일을 backupDir에 보관합니다.
# - 같은 파일을 여러 task가 건드려도 중복 백업하지 않습니다.

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Set

_BACKED_UP: Set[str] = set()


def backup_files(files: Iterable[str | Path], backup_dir: str | Path, game_id: str = "unknown") -> List[str]:
    backup_root = Path(backup_dir).resolve()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_dir = backup_root / game_id / stamp
    target_dir.mkdir(parents=True, exist_ok=True)

    backed_up_paths: List[str] = []

    for file in files:
        src = Path(file).resolve()

        if not src.exists():
            continue

        key = str(src).lower()
        if key in _BACKED_UP:
            continue

        dst = target_dir / src.name
        shutil.copy2(src, dst)

        _BACKED_UP.add(key)
        backed_up_paths.append(str(dst))

    return backed_up_paths


# 최신 백업 폴더 찾기
def find_latest_backup_dir(backup_dir: str | Path, game_id: str) -> Path:
    game_backup_root = Path(backup_dir).resolve() / game_id

    if not game_backup_root.exists():
        raise FileNotFoundError(f"Backup root not found: {game_backup_root}")

    candidates = [p for p in game_backup_root.iterdir() if p.is_dir()]

    if not candidates:
        raise FileNotFoundError(f"No backup folders found in: {game_backup_root}")

    return sorted(candidates, key=lambda p: p.name)[-1]


# 백업 폴더의 파일들을 대상 dataDir로 복원
def restore_backup(
        backup_dir: str | Path,
        game_id: str,
        data_dir: str | Path,
        backup_stamp: str | None = None
) -> list[str]:
    game_backup_root = Path(backup_dir).resolve() / game_id

    if backup_stamp:
        source_dir = game_backup_root / backup_stamp
    else:
        source_dir = find_latest_backup_dir(backup_dir, game_id)

    if not source_dir.exists():
        raise FileNotFoundError(f"Backup folder not found: {source_dir}")

    target_dir = Path(data_dir).resolve()
    restored: list[str] = []

    for src in source_dir.iterdir():
        if not src.is_file():
            continue

        dst = target_dir / src.name
        shutil.copy2(src, dst)
        restored.append(str(dst))

    return restored
