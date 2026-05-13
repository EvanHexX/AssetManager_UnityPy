# asset_patcher/core/ui_texture_metadata.py
# 설명:
# UI Texture2D 패치 대상 TSV를 로드하고 pathID/name 기준으로 조회한다.

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UiTextureMetadata:
    category: str
    group: str
    display_name: str
    texture_name: str
    path_id: int
    size: tuple[int, int]
    texture_format: str
    assets_file: str
    flip_y: bool


class UiTextureMetadataStore:
    """
    UI texture metadata TSV 로더.
    """

    def __init__(self, tsv_path: str | Path) -> None:
        self.tsv_path = Path(tsv_path)
        self._items: list[UiTextureMetadata] = []
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return

        if not self.tsv_path.exists():
            raise FileNotFoundError(f"UI texture metadata TSV가 없습니다: {self.tsv_path}")

        with self.tsv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter="\t")

            required_columns = {
                "category",
                "group",
                "display_name",
                "texture_name",
                "pathID",
                "width",
                "height",
                "format",
                "assets_file",
                "flip_y",
            }
            missing_columns = required_columns - set(reader.fieldnames or [])

            if missing_columns:
                raise ValueError(
                    f"UI texture metadata TSV 필수 컬럼 누락: {sorted(missing_columns)}"
                )

            for row in reader:
                self._items.append(
                    UiTextureMetadata(
                        category=row["category"].strip(),
                        group=row["group"].strip(),
                        display_name=row["display_name"].strip(),
                        texture_name=row["texture_name"].strip(),
                        path_id=int(row["pathID"]),
                        size=(int(row["width"]), int(row["height"])),
                        texture_format=row["format"].strip(),
                        assets_file=row["assets_file"].strip(),
                        flip_y=self._parse_bool(row["flip_y"]),
                    )
                )

        self._loaded = True

    def all(self) -> list[UiTextureMetadata]:
        self.load()
        return list(self._items)

    def find(
        self,
        path_id: int | None = None,
        texture_name: str | None = None,
    ) -> UiTextureMetadata:
        """
        pathID 또는 texture_name으로 UI texture metadata를 하나 찾는다.
        """

        self.load()

        matches = self._items

        if path_id is not None:
            matches = [item for item in matches if item.path_id == int(path_id)]

        if texture_name is not None:
            normalized_name = texture_name.strip()
            matches = [item for item in matches if item.texture_name == normalized_name]

        if len(matches) != 1:
            raise ValueError(
                "UI texture metadata 매칭 실패: "
                f"pathID={path_id}, texture_name={texture_name}, matches={len(matches)}"
            )

        return matches[0]

    @staticmethod
    def _parse_bool(value: str) -> bool:
        return value.strip().lower() in ("1", "true", "yes", "y")
