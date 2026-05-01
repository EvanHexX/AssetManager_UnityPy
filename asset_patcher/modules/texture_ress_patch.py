# asset_patcher/modules/texture_ress_patch.py
# 설명:
# - Unity Texture2D의 m_StreamData를 기준으로 .resS 파일만 직접 패치합니다.
# - .assets 파일은 변경하지 않습니다.
# - 같은 이름 Texture가 여러 개 있을 수 있으므로 pathId 기준을 우선합니다.

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, Optional

import UnityPy
from PIL import Image, ImageOps
from asset_patcher.core.backup import backup_files


def _get_attr(obj: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    return default


def run_texture_ress_patch(task: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
    assets_path = Path(task["assetsFile"]).resolve()

    target = task.get("target", {})
    source = task.get("source", {})
    patch = task.get("patch", {})

    path_id = target.get("pathId")
    texture_name = target.get("textureName")
    png_path = Path(source["png"]).resolve()

    output_dir = Path(options.get("outputDir") or assets_path.parent).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    dry_run = bool(options.get("dryRun", False))
    overwrite_original = bool(options.get("overwriteOriginal", False))

    if not assets_path.exists():
        raise FileNotFoundError(f"assetsFile not found: {assets_path}")

    if not png_path.exists():
        raise FileNotFoundError(f"png not found: {png_path}")

    env = UnityPy.load(str(assets_path))

    target_data = None
    target_obj = None

    for obj in env.objects:
        if obj.type.name != "Texture2D":
            continue

        if path_id is not None and obj.path_id != int(path_id):
            continue

        data = obj.read(check_read=False)
        data_name = _get_attr(data, "name", "m_Name")

        if path_id is not None or data_name == texture_name:
            target_obj = obj
            target_data = data
            break

    if target_data is None:
        raise RuntimeError(
            f"Texture2D not found. pathId={path_id}, textureName={texture_name}"
        )

    data_name = _get_attr(target_data, "name", "m_Name")
    width = int(target_data.m_Width)
    height = int(target_data.m_Height)
    texture_format = str(target_data.m_TextureFormat)

    expected_width = target.get("expectedWidth")
    expected_height = target.get("expectedHeight")

    if expected_width is not None and width != int(expected_width):
        raise RuntimeError(f"Width mismatch. actual={width}, expected={expected_width}")

    if expected_height is not None and height != int(expected_height):
        raise RuntimeError(f"Height mismatch. actual={height}, expected={expected_height}")

    stream = target_data.m_StreamData
    offset = int(_get_attr(stream, "offset", "Offset"))
    size = int(_get_attr(stream, "size", "Size"))
    stream_path = _get_attr(stream, "path", "Path", default="")

    if not stream_path:
        raise RuntimeError("Texture2D does not use external .resS stream data.")

    img = Image.open(png_path).convert("RGBA")

    if patch.get("requireSameSize", True) and img.size != (width, height):
        raise RuntimeError(
            f"PNG size mismatch. png={img.size}, texture={width}x{height}"
        )

    if patch.get("flipY", True):
        img = ImageOps.flip(img)

    raw = img.tobytes("raw", "RGBA")

    if len(raw) != size:
        raise RuntimeError(
            f"Raw byte size mismatch. raw={len(raw)}, stream={size}. "
            f"format={texture_format}"
        )

    ress_path = _resolve_ress_path(assets_path, stream_path, task.get("ressFile"))

    if not ress_path.exists():
        raise FileNotFoundError(f"resS file not found: {ress_path}")

    if options.get("backup", True):
        _backup_dir = options.get("backupDir")
        game_id = options.get("_gameId", "unknown")
        if _backup_dir:
            backup_dir = Path(str(_backup_dir))
            backup_files(
                [assets_path, ress_path],
                backup_dir=backup_dir,
                game_id=game_id
            )
    if dry_run:
        return {
            "taskId": task["id"],
            "status": "dry_run",
            "textureName": data_name,
            "pathId": target_obj.path_id if target_obj else path_id,
            "size": f"{width}x{height}",
            "streamOffset": offset,
            "streamSize": size,
            "ressFile": str(ress_path)
        }

    if overwrite_original:
        out_assets = assets_path
        out_ress = ress_path
    else:
        out_assets = output_dir / assets_path.name
        out_ress = output_dir / ress_path.name
        shutil.copy2(assets_path, out_assets)
        shutil.copy2(ress_path, out_ress)

    with out_ress.open("r+b") as f:
        f.seek(offset)
        f.write(raw)

    return {
        "taskId": task["id"],
        "status": "success",
        "textureName": data_name,
        "pathId": target_obj.path_id if target_obj else path_id,
        "size": f"{width}x{height}",
        "format": texture_format,
        "assetsFile": str(out_assets),
        "ressFile": str(out_ress)
    }


def _resolve_ress_path(
        assets_path: Path,
        stream_path: str,
        explicit_ress_file: Optional[str]
) -> Path:
    if explicit_ress_file:
        return Path(explicit_ress_file).resolve()

    stream_name = Path(str(stream_path).replace("\\", "/")).name

    if stream_name:
        candidate = assets_path.with_name(stream_name)
        if candidate.exists():
            return candidate

    return assets_path.with_name(assets_path.name + ".resS")
