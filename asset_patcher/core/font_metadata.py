# asset_patcher/core/font_metadata.py
# 설명:
# fonts_data.tsv를 기준으로 Font 패치 대상을 검증한다.
# Arial도 포함하며, 제외가 필요하면 TSV에서 해당 행을 삭제한다.

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FontMetadata:
    name: str
    description: str
    type_name: str
    path_id: int
    source: str


class FontMetadataStore:
    def __init__(self, tsv_path: str | Path) -> None:
        self.tsv_path = Path(tsv_path)
        self._items: list[FontMetadata] = []
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return

        if not self.tsv_path.exists():
            raise FileNotFoundError(f"Font metadata TSV가 없습니다: {self.tsv_path}")

        with self.tsv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter="\t")

            for row in reader:
                self._items.append(
                    FontMetadata(
                        name=row["Name"],
                        description=row["Description"],
                        type_name=row["Type"],
                        path_id=int(row["PathID"]),
                        source=row["Source"],
                    )
                )

        self._loaded = True

    def find_by_name(self, name: str) -> FontMetadata:
        self.load()

        matches = [item for item in self._items if item.name == name]

        if len(matches) != 1:
            raise ValueError(f"Font metadata 매칭 실패: name={name}, matches={len(matches)}")

        return matches[0]

    def find_by_path_id(self, path_id: int) -> FontMetadata:
        self.load()

        matches = [item for item in self._items if item.path_id == path_id]

        if len(matches) != 1:
            raise ValueError(f"Font metadata 매칭 실패: pathID={path_id}, matches={len(matches)}")

        return matches[0]

    def list_all(self) -> list[FontMetadata]:
        self.load()
        return list(self._items)