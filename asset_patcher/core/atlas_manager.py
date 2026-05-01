# asset_patcher/core/atlas_manager.py
# 설명:
# Spine atlas txt 파일을 실행 중 한 번만 로드하고, 여러 패치 요청의 atlas 변경을 누적한 뒤 한 번만 저장한다.
# 현재 대상 atlas 형식:
#   skeleton.png
#   size:2487,1081
#   filter:Linear,Linear
#   pma:true
#   scale:0.88
#   -100/右臂
#   bounds:1879,627,126,452
#   offsets:0,0,126,455

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


@dataclass
class AtlasPageInfo:
    """
    atlas page 정보를 표현한다.

    Args:
        page_name: atlas page 이름. 예: skeleton.png, skeleton_2.png
        size: page size. 예: (2487, 1081)
        start_line: page block 시작 줄 index
        end_line: page block 종료 줄 index
    """

    page_name: str
    size: tuple[int, int]
    start_line: int
    end_line: int


class AtlasDocument:
    """
    하나의 atlas txt 문서를 메모리에 로드하고 수정한다.
    """

    def __init__(self, atlas_path: str | Path) -> None:
        """
        AtlasDocument를 초기화한다.

        Args:
            atlas_path: atlas txt 파일 경로
        """

        self.atlas_path = Path(atlas_path)
        self.lines: list[str] = []
        self.dirty = False

    def load(self) -> None:
        """
        atlas txt 파일을 로드한다.

        Raises:
            FileNotFoundError: atlas 파일이 없을 경우
        """

        if not self.atlas_path.exists():
            raise FileNotFoundError(f"atlas 파일이 없습니다: {self.atlas_path}")

        self.lines = self.atlas_path.read_text(encoding="utf-8").splitlines()
        self.dirty = False

    def save(self) -> None:
        """
        dirty 상태일 때만 atlas txt 파일을 저장한다.
        """

        if not self.dirty:
            return

        self.atlas_path.write_text(
            "\n".join(self.lines) + "\n",
            encoding="utf-8",
        )
        self.dirty = False

    def backup_original_once(self) -> Path:
        """
        원본 atlas txt 백업을 최초 1회만 생성한다.

        Returns:
            백업 파일 경로
        """

        backup_path = self.atlas_path.with_suffix(self.atlas_path.suffix + ".original")

        if not backup_path.exists():
            shutil.copy2(self.atlas_path, backup_path)

        return backup_path

    def find_page(self, texture_name: str) -> AtlasPageInfo | None:
        """
        atlas 문서에서 texture_name에 해당하는 page block을 찾는다.

        Args:
            texture_name: atlas page 이름. 예: skeleton.png, skeleton_2.png

        Returns:
            AtlasPageInfo 또는 None
        """

        normalized = texture_name.strip()

        for index, line in enumerate(self.lines):
            if line.strip() != normalized:
                continue

            size = self._read_page_size(index)

            if size is None:
                return None

            end_line = self._find_page_end(index)

            return AtlasPageInfo(
                page_name=normalized,
                size=size,
                start_line=index,
                end_line=end_line,
            )

        return None

    def update_page_for_png(
            self,
            texture_name: str,
            png_path: str | Path,
    ) -> dict:
        """
        PNG 크기에 맞춰 atlas page 및 하위 region 좌표를 필요 시 배율 수정한다.

        Args:
            texture_name: atlas page 이름
            png_path: 새 PNG 파일 경로

        Returns:
            수정 결과 dict

        Raises:
            FileNotFoundError: PNG 파일이 없을 경우
            ValueError: atlas page가 없거나 비율이 다를 경우
        """

        png_path = Path(png_path)

        if not png_path.exists():
            raise FileNotFoundError(f"PNG 파일이 없습니다: {png_path}")

        with Image.open(png_path) as img:
            new_w, new_h = img.size

        page = self.find_page(texture_name)

        if page is None:
            raise ValueError(f"atlas에서 page를 찾지 못했습니다: {texture_name}")

        old_w, old_h = page.size

        if (old_w, old_h) == (new_w, new_h):
            return {
                "texture_name": texture_name,
                "changed": False,
                "reason": "same_size",
                "old_size": [old_w, old_h],
                "new_size": [new_w, new_h],
            }

        scale_x = new_w / old_w
        scale_y = new_h / old_h

        if abs(scale_x - scale_y) > 0.0001:
            raise ValueError(
                "atlas 비율 불일치: "
                f"texture={texture_name}, old={old_w}x{old_h}, new={new_w}x{new_h}"
            )

        scale = scale_x

        self.backup_original_once()

        self._write_page_size(page.start_line, new_w, new_h)

        changed_fields = self._scale_page_region_values(
            start_line=page.start_line,
            end_line=page.end_line,
            scale=scale,
        )

        self.dirty = True

        return {
            "texture_name": texture_name,
            "changed": True,
            "reason": "scaled",
            "scale": scale,
            "old_size": [old_w, old_h],
            "new_size": [new_w, new_h],
            "changed_fields": changed_fields,
        }

    def _read_page_size(self, page_line_index: int) -> tuple[int, int] | None:
        """
        page block의 header size 줄을 읽는다.

        Args:
            page_line_index: page 이름이 있는 줄 index

        Returns:
            (width, height) 또는 None
        """

        for i in range(page_line_index + 1, min(page_line_index + 8, len(self.lines))):
            stripped = self.lines[i].strip()

            if not stripped.startswith("size:"):
                continue

            values = self._parse_int_values(stripped)

            if len(values) != 2:
                return None

            return values[0], values[1]

        return None

    def _write_page_size(self, page_line_index: int, width: int, height: int) -> None:
        """
        page block의 header size 줄을 새 크기로 수정한다.

        Args:
            page_line_index: page 이름이 있는 줄 index
            width: 새 width
            height: 새 height

        Raises:
            ValueError: size 줄을 찾지 못한 경우
        """

        for i in range(page_line_index + 1, min(page_line_index + 8, len(self.lines))):
            line = self.lines[i]

            if not line.strip().startswith("size:"):
                continue

            indent = line[: len(line) - len(line.lstrip())]
            self.lines[i] = f"{indent}size:{width},{height}"
            return

        raise ValueError(f"page size 줄을 찾지 못했습니다: line={page_line_index}")

    def _find_page_end(self, page_line_index: int) -> int:
        """
        현재 page block의 종료 줄 index를 찾는다.

        실제 atlas 기준:
            page_name
            size:...
            filter:...
            pma:...
            scale:...
            region...

            next_page_name
            size:...

        Args:
            page_line_index: page 이름이 있는 줄 index

        Returns:
            page block 종료 줄 index
        """

        for i in range(page_line_index + 1, len(self.lines)):
            line = self.lines[i]
            stripped = line.strip()

            if not stripped:
                continue

            # ✅ page 이름 후보:
            # - 들여쓰기 없음
            # - 콜론 없음
            # - 다음 몇 줄 안에 size:가 있음
            # - region 이름처럼 "/"로 시작하지 않음
            if line == stripped and ":" not in stripped and not stripped.startswith("-"):
                if self._read_page_size(i) is not None:
                    return i - 1

        return len(self.lines) - 1

    def _scale_page_region_values(
            self,
            start_line: int,
            end_line: int,
            scale: float,
    ) -> list[str]:
        """
        page block 내부 region 값을 배율 수정한다.

        실제 대상:
            bounds:x,y,w,h
            offsets:x,y,w,h

        수정하지 않는 대상:
            rotate:90
            filter
            pma
            scale

        Args:
            start_line: page block 시작 줄
            end_line: page block 종료 줄
            scale: 적용 배율

        Returns:
            변경된 field 이름 목록
        """

        scalable_4_keys = {"bounds", "offsets"}
        changed_fields: list[str] = []

        for i in range(start_line + 1, end_line + 1):
            line = self.lines[i]
            stripped = line.strip()

            if ":" not in stripped:
                continue

            key = stripped.split(":", 1)[0].strip()

            if key not in scalable_4_keys:
                continue

            values = self._parse_int_values(stripped)

            if len(values) != 4:
                continue

            scaled_values = [round(value * scale) for value in values]

            indent = line[: len(line) - len(line.lstrip())]
            self.lines[i] = f"{indent}{key}:{','.join(map(str, scaled_values))}"
            changed_fields.append(key)

        return changed_fields

    @staticmethod
    def _parse_int_values(line: str) -> list[int]:
        """
        'key:1,2,3,4' 또는 'key: 1, 2, 3, 4' 형태의 정수 값을 파싱한다.

        Args:
            line: atlas 줄 문자열

        Returns:
            정수 리스트
        """

        if ":" not in line:
            return []

        value_part = line.split(":", 1)[1]

        return [int(value) for value in re.findall(r"-?\d+", value_part)]


class AtlasManager:
    """
    여러 atlas txt 파일을 캐싱하고, 누적 수정 후 저장한다.
    """

    def __init__(self) -> None:
        """
        AtlasManager를 초기화한다.
        """

        self._documents: dict[Path, AtlasDocument] = {}

    def get_document(self, atlas_path: str | Path) -> AtlasDocument:
        """
        atlas 문서를 캐시에서 가져오거나 새로 로드한다.

        Args:
            atlas_path: atlas txt 경로

        Returns:
            AtlasDocument
        """

        path = Path(atlas_path).resolve()

        if path not in self._documents:
            document = AtlasDocument(path)
            document.load()
            self._documents[path] = document

        return self._documents[path]

    def update_page_for_png(
            self,
            atlas_path: str | Path,
            texture_name: str,
            png_path: str | Path,
    ) -> dict:
        """
        atlas_path에 해당하는 문서를 가져와 texture_name page를 PNG 크기에 맞게 수정한다.

        Args:
            atlas_path: atlas txt 파일 경로
            texture_name: atlas page 이름
            png_path: 새 PNG 파일 경로

        Returns:
            수정 결과 dict
        """

        document = self.get_document(atlas_path)

        return document.update_page_for_png(
            texture_name=texture_name,
            png_path=png_path,
        )

    def save_all(self) -> None:
        """
        dirty 상태의 모든 atlas 문서를 저장한다.
        """

        for document in self._documents.values():
            document.save()