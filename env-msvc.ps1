param (
  [Parameter(Mandatory=$true)][string]$TARGET_ARCH
)

${global:PARALLEL_JOBS} = ${env:NUMBER_OF_PROCESSORS}

# >>> VS DevShell >>>
# Only supports access to the VS DevShell from PowerShell
# see https://learn.microsoft.com/visualstudio/ide/reference/command-prompt-powershell#developer-powershell
$HOST_ARCH = ${env:PROCESSOR_ARCHITECTURE}.ToLower()

# Alreay accessed the VS DevShell
${script:VSCMD_ARG_TGT_ARCH} = ${env:VSCMD_ARG_TGT_ARCH}
if (${script:VSCMD_ARG_TGT_ARCH} -ne $null) {
  if (${script:VSCMD_ARG_TGT_ARCH} -ieq "x64") {
    ${script:VSCMD_ARG_TGT_ARCH} = "amd64"
  }
  if (${script:VSCMD_ARG_TGT_ARCH} -ieq $TARGET_ARCH) {
    exit 0
  }
}
$VS_DEVCMD_ARGS = "-host_arch=${HOST_ARCH} -arch=${TARGET_ARCH}"


${global:CCACHE_SRC} = ""
$ccache = Get-Command -Name ccache.exe -CommandType Application -ErrorAction SilentlyContinue
if ($ccache -ne $null) {
  ${global:CCACHE_SRC} = "ccache.exe"

  # https://github.com/ccache/ccache/discussions/978
  ${global:CMAKE_EXTRA} = "${global:CMAKE_EXTRA} -D CMAKE_C_COMPILER_LAUNCHER=ccache.exe"
  ${global:CMAKE_EXTRA} = "${global:CMAKE_EXTRA} -D CMAKE_CXX_COMPILER_LAUNCHER=ccache.exe"
}


function vsdevsh {
  param (
    [Parameter(Mandatory=$true)][string]$VS_PATH
  )

  $VS_PS1 = "${VS_PATH}\Common7\Tools\Microsoft.VisualStudio.DevShell.dll"
  if (-not (Test-Path -PathType Leaf -Path "${VS_PS1}")) {
    return $false
  }
  Write-Host -ForegroundColor Green "Enter VS DevShell via PS1"
  Import-Module "${VS_PS1}"
  Enter-VsDevShell -VsInstallPath "${VS_PATH}" -SkipAutomaticLocation -DevCmdArguments "${VS_DEVCMD_ARGS}"
  return $true
}

# Set VS search path
$MSVC_INSTALL_DIR_64BIT="C:\Program Files\Microsoft Visual Studio"
$MSVC_INSTALL_DIR_32BIT="C:\Program Files (x86)\Microsoft Visual Studio"

$MSVC_SKIP_AUTO_SEARCH = ${env:MSVC_SKIP_AUTO_SEARCH}
if ($MSVC_SKIP_AUTO_SEARCH -eq $null) {
  $MSVC_SKIP_AUTO_SEARCH = "0"
}
if ($MSVC_SKIP_AUTO_SEARCH -ieq "0") {
  $VS_SEARCH_PATH = @(
    "${MSVC_INSTALL_DIR_64BIT}\2022\BuildTools",
    "${MSVC_INSTALL_DIR_64BIT}\2022\Community",
    "${MSVC_INSTALL_DIR_64BIT}\2022\Professional",
    "${MSVC_INSTALL_DIR_64BIT}\2022\Enterprise",
    "${MSVC_INSTALL_DIR_64BIT}\2019\BuildTools",
    "${MSVC_INSTALL_DIR_64BIT}\2019\Community",
    "${MSVC_INSTALL_DIR_64BIT}\2019\Professional",
    "${MSVC_INSTALL_DIR_64BIT}\2019\Enterprise",

    "${MSVC_INSTALL_DIR_32BIT}\2022\BuildTools",
    "${MSVC_INSTALL_DIR_32BIT}\2022\Community",
    "${MSVC_INSTALL_DIR_32BIT}\2022\Professional",
    "${MSVC_INSTALL_DIR_32BIT}\2022\Enterprise",
    "${MSVC_INSTALL_DIR_32BIT}\2019\BuildTools",
    "${MSVC_INSTALL_DIR_32BIT}\2019\Community",
    "${MSVC_INSTALL_DIR_32BIT}\2019\Professional",
    "${MSVC_INSTALL_DIR_32BIT}\2019\Enterprise"
  )
} else {
  $VS_SEARCH_PATH = @( "${env:MSVC_INSTALL_DIR}" )
}

$vs_devshell_ok = $false
foreach ($VS_PATH in $VS_SEARCH_PATH) {
  $vs_devshell_ok = vsdevsh "$VS_PATH"
  if ($vs_devshell_ok) { break }
}
if (-not $vs_devshell_ok) {
  Write-Error -Message "Failed to search MSVC environment."
  exit 1
}

if (${HOST_ARCH} -ieq "amd64") { ${global:TARGET_TRIPLE} = "x86_64-pc-windows-msvc" }
if (${HOST_ARCH} -ieq "arm64") { ${global:TARGET_TRIPLE} = "aarch64-pc-windows-msvc" }

${script:HOSTCC} = Join-Path -Path "${env:VCToolsInstallDir}" `
  "bin/host${env:VSCMD_ARG_HOST_ARCH}" "${env:VSCMD_ARG_HOST_ARCH}" "cl.exe"
${global:CMAKE_EXTRA} = @"
${global:CMAKE_EXTRA} ``
-D CMAKE_CROSSCOMPILING:BOOL=TRUE -D CMAKE_SYSTEM_NAME=Windows ``
-D CMAKE_C_HOST_COMPILER='${script:HOSTCC}' ``
-D CMAKE_CXX_HOST_COMPILER='${script:HOSTCC}'
"@
# <<< VS DevShell <<<
