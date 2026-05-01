# scripts/init_project_dirs.ps1
# 설명:
# AssetManager_UnityPy 기본 폴더와 빈 __init__.py 파일을 생성한다.

$dirs = @(
  "asset_patcher",
  "asset_patcher/models",
  "asset_patcher/core",
  "asset_patcher/modules",
  "asset_patcher/services",
  "metadata",
  "examples",
  "originals",
  "reports",
  "scripts"
)

$files = @(
  "asset_patcher/__init__.py",
  "asset_patcher/models/__init__.py",
  "asset_patcher/core/__init__.py",
  "asset_patcher/modules/__init__.py",
  "asset_patcher/services/__init__.py"
)

foreach ($dir in $dirs) {
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  Write-Host "[DIR] $dir"
}

foreach ($file in $files) {
  New-Item -ItemType File -Force -Path $file | Out-Null
  Write-Host "[FILE] $file"
}