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

## 실행예시
### 최신 백업 복원
```powershell
python -m asset_patcher.cli --plan ".\examples\patch_plan.example.json" --restore-latest 
```
### 특정 백업 복원
```powershell
python -m asset_patcher.cli --plan ".\examples\patch_plan.example.json" --restore-stamp "20260501_103012"
```