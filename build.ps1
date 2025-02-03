param (
  [Parameter(Mandatory=$false)][string]${private:PKG_NAME},
  [Parameter(Mandatory=$false)][string]${private:PKG_TYPE} = "static"
)

# Powershell windows runner always succeeding
#  - https://gitlab.com/gitlab-org/gitlab-runner/-/issues/1514
$ErrorActionPreference = 'Stop'

${private:PWSH_VERSION} = ${Host}.Version
if ((${private:PWSH_VERSION}.Major -ge 6) -and (-not $IsWindows)) {
  Write-Error -Message "'${PSCommandPath}' is only supported on Windows."
  exit 1
}

$PROJ_ROOT = $PSScriptRoot
$PYPI_MIRROR = "-i https://mirrors.bfsu.edu.cn/pypi/web/simple"

${private:triplet} = [System.IO.Path]::GetFileNameWithoutExtension($PSCommandPath)
${private:triplet_values} = $triplet -split '_'
${private:triplet_length} = $triplet_values.Length
if ($triplet_length -lt 3) {
  Write-Error -Message `
    "Please use wrapper to build the project, such as 'build_`${platform}_`${arch}.ps1'."
  exit 1
}
${private:TARGET_PLATFORM} = $triplet_values[1]
${private:prefix} = $triplet_values[0] + "_" + $triplet_values[1] + "_"
${private:TARGET_ARCH} = $triplet.Substring($prefix.Length)

switch ($TARGET_PLATFORM) {
  'win-msvc' {
    . "${PROJ_ROOT}\env-msvc.ps1" ${TARGET_ARCH}
    if (($LASTEXITCODE -ne $null) -and ($LASTEXITCODE -ne 0)) {
      exit $LASTEXITCODE
    }
    break
  }
}

${private:compile} = {
  param (
    [Parameter(Mandatory=$true)][string]$PKG_NAME,
    [Parameter(Mandatory=$true)][string]$PKG_TYPE,
    [Parameter(Mandatory=$true)][string]$PKG_PLATFORM,
    [Parameter(Mandatory=$true)][string]$PKG_ARCH
  )

  ${SUBPROJ_SRC} = "${PROJ_ROOT}\deps\${PKG_NAME}"

  ${PKG_BULD_DIR} = "${PROJ_ROOT}\tmp\${PKG_NAME}\${PKG_PLATFORM}\${PKG_ARCH}"
  ${PKG_INST_DIR} = "${PROJ_ROOT}\out\${PKG_NAME}\${PKG_PLATFORM}\${PKG_ARCH}"
  if (${env:GITHUB_ACTIONS} -ieq "true") {
    if (${env:BULD_DIR} -ne $null) { ${PKG_BULD_DIR} = "${env:BULD_DIR}" }
    if (${env:INST_DIR} -ne $null) { ${PKG_INST_DIR} = "${env:INST_DIR}" }
  }

  # MSYS2
  ${MSYS2_BASH_CMD} = "C:/msys64/usr/bin/bash.exe"
  if (${env:MSYS2_BASH_CMD} -ne $null) {
    ${MSYS2_BASH_CMD} = ${env:MSYS2_BASH_CMD}
  }

  ${env:MSYS2_PATH_TYPE} = "inherit"
  ${MSYS2_BASH_TXT} = @"
set -e

export PROJ_ROOT=`$(cygpath -u "${PROJ_ROOT}")
export PYPI_MIRROR="${PYPI_MIRROR}"

export PKG_NAME="${PKG_NAME}"
export SUBPROJ_SRC=`$(cygpath -u "${SUBPROJ_SRC}")

export PKG_TYPE="${PKG_TYPE}"
export PKG_PLATFORM="${PKG_PLATFORM}"
export PKG_ARCH="${PKG_ARCH}"
export PKG_ARCH_LIBC="${PKG_ARCH}"

export PKG_BULD_DIR=`$(cygpath -u "${PKG_BULD_DIR}")
export PKG_INST_DIR=`$(cygpath -u "${PKG_INST_DIR}")

export PARALLEL_JOBS="${PARALLEL_JOBS}"
export CCACHE_SRC="${CCACHE_SRC}"
export TARGET_TRIPLE="${TARGET_TRIPLE}"
export PKG_CONFIG_EXEC="pkgconf.exe"

export CC="cl.exe"; export CXX="cl.exe"
export LD="`$(dirname "`$(command -v cl.exe)")/link.exe"

cd `${PROJ_ROOT}; bash `${PROJ_ROOT}/scripts/`${PKG_NAME}.sh
"@

  <#
  if (-not (Test-Path -PathType Any -Path "${SUBPROJ_SRC}/.git")) {
    Push-Location "${PROJ_ROOT}"
    git submodule update --init --depth=1 --single-branch -f -- "deps/${PKG_NAME}"
    Pop-Location
  }

  if (Test-Path -PathType Container -Path "${PROJ_ROOT}/patches/${PKG_NAME}") {
    Push-Location "${SUBPROJ_SRC}"
    git reset --hard HEAD

    foreach ($patch in (Get-ChildItem -Path "${PROJ_ROOT}/patches/${PKG_NAME}" -File)) {
      git apply --verbose --ignore-space-change --ignore-whitespace ${patch}.FullName
    }
    Pop-Location
  }
  #>
  & "${PROJ_ROOT}\scripts\${PKG_NAME}.ps1"
  if (($LASTEXITCODE -ne $null) -and ($LASTEXITCODE -ne 0)) { exit $LASTEXITCODE }


  $BUILD_DATE = (Get-Date -UFormat "+%Y-%m-%dT%H:%M:%S %Z")
  Write-Host -ForegroundColor Magenta "${PKG_INST_DIR} - Build Done @${BUILD_DATE}"
}

if (($PKG_NAME -eq $null) -or ($PKG_NAME -eq "")) {
  Write-Error -Message "Please declare the module to be compiled."
  exit 1
}
Invoke-Command -ScriptBlock ${compile} `
  -ArgumentList ${PKG_NAME}, ${PKG_TYPE}, ${TARGET_PLATFORM}, ${TARGET_ARCH}
