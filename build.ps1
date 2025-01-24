param (
  [Parameter(Mandatory=$false)][string]$PKG_NAME,
  [Parameter(Mandatory=$false)][string]$PKG_TYPE = "static"
)

# Powershell windows runner always succeeding
#  - https://gitlab.com/gitlab-org/gitlab-runner/-/issues/1514
${env:ErrorActionPreference} = 'Stop'

${script:PWSH_VERSION} = ${Host}.Version
if ((${script:PWSH_VERSION}.Major -ge 6) -and (-not $IsWindows)) {
  Write-Host -ForegroundColor Red "'${PSCommandPath}' is only supported on Windows."
  exit 1
}

${global:PROJ_ROOT} = $PSScriptRoot
${global:PYPI_MIRROR} = "-i https://mirrors.bfsu.edu.cn/pypi/web/simple"

$triplet = [System.IO.Path]::GetFileNameWithoutExtension($PSCommandPath)
$triplet_values = $triplet -split '_'
$triplet_length = $triplet_values.Length
if ($triplet_length -lt 3) {
  Write-Host -ForegroundColor Red `
    "Please use wrapper to build the project, such as 'build_`${platform}_`${arch}.ps1'."
  exit 1
}
$TARGET_PLATFORM = $triplet_values[1]
$prefix = $triplet_values[0] + "_" + $triplet_values[1] + "_"
$TARGET_ARCH = $triplet.Substring($prefix.Length)

switch ($TARGET_PLATFORM) {
  'win-msvc' {
    . "${global:PROJ_ROOT}\env-msvc.ps1" ${TARGET_ARCH}
    if (($LASTEXITCODE -ne $null) -and ($LASTEXITCODE -ne 0)) {
      exit $LASTEXITCODE
    }
    break
  }
}

$compile = {
  param (
    [Parameter(Mandatory=$true)][string]$PKG_NAME,
    [Parameter(Mandatory=$true)][string]$PKG_TYPE,
    [Parameter(Mandatory=$true)][string]$PKG_PLATFORM,
    [Parameter(Mandatory=$true)][string]$PKG_ARCH
  )

  ${global:PKG_NAME} = "${PKG_NAME}"
  ${global:SUBPROJ_SRC} = "${global:PROJ_ROOT}\deps\${PKG_NAME}"

  ${global:PKG_TYPE} = "${PKG_TYPE}"
  ${global:PKG_PLATFORM} = "${PKG_PLATFORM}"
  ${global:PKG_ARCH} = "${PKG_ARCH}"

  ${global:PKG_BULD_DIR} = "${global:PROJ_ROOT}\tmp\${PKG_NAME}\${PKG_PLATFORM}\${PKG_ARCH}"
  ${global:PKG_INST_DIR} = "${global:PROJ_ROOT}\out\${PKG_NAME}\${PKG_PLATFORM}\${PKG_ARCH}"
  if (${env:GITHUB_ACTIONS} -ieq "true") {
    if (${env:BULD_DIR} -ne $null) { ${global:PKG_BULD_DIR} = "${env:BULD_DIR}" }
    if (${env:INST_DIR} -ne $null) { ${global:PKG_INST_DIR} = "${env:INST_DIR}" }
  }

  # msys2
  ${env:MSYS2_PATH_TYPE} = "inherit"
  ${global:MSYS2_CALL_BASH} = @"
set -ex

export PROJ_ROOT=`$(cygpath -u "${global:PROJ_ROOT}")
export PYPI_MIRROR="${global:PYPI_MIRROR}"

export PKG_NAME="${PKG_NAME}"
export SUBPROJ_SRC=`$(cygpath -u "${global:SUBPROJ_SRC}")

export PKG_TYPE="${PKG_TYPE}"
export PKG_PLATFORM="${PKG_PLATFORM}"
export PKG_ARCH="${PKG_ARCH}"

export PKG_BULD_DIR=`$(cygpath -u "${global:PKG_BULD_DIR}")
export PKG_INST_DIR=`$(cygpath -u "${global:PKG_INST_DIR}")

cd `${PROJ_ROOT}; bash `${PROJ_ROOT}/scripts/${PKG_NAME}.sh
"@

  if (-not (Test-Path -PathType Any -Path "${global:SUBPROJ_SRC}/.git")) {
    Push-Location "${global:PROJ_ROOT}"
    git submodule update --init --depth=1 --single-branch -f -- "deps/${PKG_NAME}"
    Pop-Location
  }

  if (Test-Path -PathType Container -Path "${global:PROJ_ROOT}/patches/${PKG_NAME}") {
    Push-Location "${global:SUBPROJ_SRC}"
    git reset --hard HEAD

    foreach ($patch in (Get-ChildItem -Path "${global:PROJ_ROOT}/patches/${PKG_NAME}" -File)) {
      git apply --verbose --ignore-space-change --ignore-whitespace ${patch}.FullName
    }
    Pop-Location
  }
  & "${global:PROJ_ROOT}\scripts\${PKG_NAME}.ps1"


  if (${env:CLANGD_CODE_COMPLETION} -ne "1") {
    Get-ChildItem "${global:PKG_INST_DIR}"
  }
  $BUILD_DATE = (Get-Date -UFormat "+%Y-%m-%dT%H:%M:%S %Z")
  Write-Host -ForegroundColor Magenta "${global:SUBPROJ_SRC} - Build Done @${BUILD_DATE}"
}

if (($PKG_NAME -eq $null) -or ($PKG_NAME -eq "")) {
  Write-Host -ForegroundColor Red "Please declare the module to be compiled."
  exit 1
}
Invoke-Command -ScriptBlock ${compile} `
  -ArgumentList ${PKG_NAME}, ${PKG_TYPE}, ${TARGET_PLATFORM}, ${TARGET_ARCH}
