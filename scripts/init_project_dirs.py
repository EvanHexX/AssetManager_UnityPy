# scripts/init_project_dirs.py
# 설명:
# AssetManager_UnityPy 기본 폴더와 빈 __init__.py 파일을 생성한다.

from __future__ import annotations

from pathlib import Path


PROJECT_DIRS = [
    "asset_patcher",
    "asset_patcher/models",
    "asset_patcher/core",
    "asset_patcher/modules",
    "asset_patcher/services",
    "metadata",
    "examples",
    "originals",
    "reports",
    "scripts",
]


INIT_FILES = [
    "asset_patcher/__init__.py",
    "asset_patcher/models/__init__.py",
    "asset_patcher/core/__init__.py",
    "asset_patcher/modules/__init__.py",
    "asset_patcher/services/__init__.py",
]


def main() -> None:
    """
    프로젝트 기본 폴더와 __init__.py 파일을 생성한다.
    """

    root = Path.cwd()

    for folder in PROJECT_DIRS:
        path = root / folder
        path.mkdir(parents=True, exist_ok=True)
        print(f"[DIR] {path}")

    for file in INIT_FILES:
        path = root / file
        path.touch(exist_ok=True)
        print(f"[FILE] {path}")


if __name__ == "__main__":
    main()