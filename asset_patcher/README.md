## AssetManager_UnityPy/asset_patcher

```text
patch_plan.json
→ plan_loader.py가 읽음
→ cli.py가 task 순회
→ texture_ress_patch.py가 실행
```

## 실행 목표

```powershell
python -m asset_patcher.cli --plan "D:\Games\Outputs\patch_plan.json"
```

또는 exe화 후:

```powershell
AssetManager_UnityPy.exe --plan "D:\Games\Outputs\patch_plan.json"
```

## 다음에 만들 내용

1. `patch_plan.schema.json`
2. `plan_loader.py`
3. `texture_ress_patch.py`
4. `cli.py`
---
## 실행예시
### 최신 백업 복원
```powershell
python -m asset_patcher.cli --plan ".\examples\patch_plan.example.json" --restore-latest 
```
### 특정 백업 복원
```powershell
python -m asset_patcher.cli --plan ".\examples\patch_plan.example.json" --restore-stamp "20260501_103012"
```
---
### Font 원본 추출
#### Json:
```Json
{
  "kind": "font_extract",
  "game_id": "LongYinLiZhiZhuan",
  "font_metadata_path": "../metadata/fonts_data.tsv",
  "originals_dir": "../originals",
  "assets_file": "D:/Games/SteamLibrary/steamapps/common/LongYinLiZhiZhuan/LongYinLiZhiZhuan_Data/resources.assets",
  "overwrite": false
}
```
#### 실행:
```PowerShell
python -m asset_patcher.cli `
  --plan .\examples\font_extract.example.json `
  --report .\reports\font_extract_report.json
```
### Font 교체
#### Json:
```Json
{
  "kind": "font",
  "game_id": "LongYinLiZhiZhuan",
  "dry_run": false,
  "stop_on_error": true,
  "font_metadata_path": "../metadata/fonts_data.tsv",
  "originals_dir": "../originals",
  "assets_file": "D:/Games/SteamLibrary/steamapps/common/LongYinLiZhiZhuan/LongYinLiZhiZhuan_Data/resources.assets",
  "output_file": null,
  "jobs": [
    {
      "font_name": "Arial",
      "replacement_font_file": "D:/Mods/fonts/MyKoreanFont.ttf"
    }
  ]
}
```
### Font 복원
#### Json:
```Json
{
  "kind": "font_restore",
  "game_id": "LongYinLiZhiZhuan",
  "dry_run": false,
  "stop_on_error": true,
  "font_metadata_path": "../metadata/fonts_data.tsv",
  "originals_dir": "../originals",
  "assets_file": "D:/Games/SteamLibrary/steamapps/common/LongYinLiZhiZhuan/LongYinLiZhiZhuan_Data/resources.assets",
  "jobs": [
    {
      "path_id": 2418
    }
  ]
}
```
---
## 현재까지 CLI에서 가능한 작업:
```text
kind=clothes       의상 PNG 패치
kind=font_extract  원본 폰트 추출
kind=font          폰트 교체
kind=font_restore  원본 폰트 복원
```