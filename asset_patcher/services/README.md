### clothes patch 사용예시
```Python
from asset_patcher.services.clothes_patch_service import ClothesPatchService

service = ClothesPatchService(
    texture_metadata_path="metadata/data.tsv",
)

result = service.patch_one(
    request_data={
        "game_id": "LongYinLiZhiZhuan",
        "category": "clothes",
        "option1": "female",
        "option2": "type_01",
        "texture_name": "skeleton_17",
        "pathID": 123456,
        "size": [1763, 1050],
    },
    assets_file="D:/Games/.../sharedassets1.assets",
    png_file="D:/Mods/.../skeleton_17.png",
    atlas_file="D:/Games/.../skeleton.atlas.txt",
    dry_run=False,
)

service.save_atlas_all()
```
---
### batch job 예시
```Json
[
  {
    "request": {
      "game_id": "LongYinLiZhiZhuan",
      "category": "clothes",
      "option1": "female",
      "option2": "type_01",
      "texture_name": "skeleton_17",
      "pathID": 123456,
      "size": [1763, 1050]
    },
    "assets_file": "D:/Games/.../sharedassets1.assets",
    "png_file": "D:/Mods/female/type_01/skeleton_17.png",
    "atlas_file": "D:/Games/.../skeleton.atlas.txt",
    "output_assets_file": null,
    "flip_y": false
  }
]
```
---
### 현재 흐름
#### Batch Service
```text
React/Electron
→ batch jobs
→ ClothesBatchPatchService
→ ClothesPatchService
→ PNG 크기 비교
   ├─ 동일 크기: resS 직접 patch
   └─ 크기 변경: UnityPy Texture2D patch
→ atlas 누적 수정
→ 모든 작업 성공 시 atlas 1회 저장
```

#### 단일
```text
React 요청
→ PatchRequest
→ data.tsv 정확 검증
→ PNG 크기 확인
1. PNG 크기 확인
2. PNG 크기가 data.tsv 원본 size와 같음
   → resS patch only
   → atlas skip

3. PNG 크기가 data.tsv 원본 size와 다름
   → atlas 정보 필요
   → atlas_file 필요
   → 실제 atlas 현재 page size 확인
      - 현재 atlas size == PNG size
        → atlas skip
      - 현재 atlas size != PNG size
        → 현재 atlas size 기준으로 atlas 배율 수정
→ atlas 변경 누적
→ save_atlas_all()
```
