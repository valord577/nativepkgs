param (
  [Parameter(Mandatory=$true)][string]$TARGET_PLATFORM,
  [Parameter(Mandatory=$true)][string]$TARGET_ARCH
)

${env:PARALLEL_JOBS} = ${env:NUMBER_OF_PROCESSORS}

${env:CCACHE_SRC} = ""
$ccache = Get-Command -Name ccache.exe -CommandType Application -ErrorAction SilentlyContinue
if ($ccache -ne $null) {
  ${env:CCACHE_SRC} = "$($ccache.Source)"

  # https://github.com/ccache/ccache/discussions/978
  ${env:CMAKE_EXTRA_ARGS} = "${env:CMAKE_EXTRA_ARGS} -D CMAKE_C_COMPILER_LAUNCHER=`"${env:CCACHE_SRC}`""
  ${env:CMAKE_EXTRA_ARGS} = "${env:CMAKE_EXTRA_ARGS} -D CMAKE_CXX_COMPILER_LAUNCHER=`"${env:CCACHE_SRC}`""
}

# >>> VS DevShell >>>
# Only supports access to the VS DevShell from PowerShell
# see https://learn.microsoft.com/visualstudio/ide/reference/command-prompt-powershell#developer-powershell
$HOST_ARCH = ${env:PROCESSOR_ARCHITECTURE}.ToLower()

# Alreay accessed the VS DevShell
$VSCMD_ARG_TGT_ARCH = ${env:VSCMD_ARG_TGT_ARCH}
if ($VSCMD_ARG_TGT_ARCH -ne $null) {
  if ($VSCMD_ARG_TGT_ARCH -ieq "x64") {
    $VSCMD_ARG_TGT_ARCH = "amd64"
  }
  if ($VSCMD_ARG_TGT_ARCH -ieq $TARGET_ARCH) {
    exit 0
  }
}
$VS_DEVCMD_ARGS = "-host_arch=${HOST_ARCH} -arch=${TARGET_ARCH}"

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
$MSVC_INSTALL_DIR = ${env:MSVC_INSTALL_DIR}
if ($MSVC_INSTALL_DIR -eq $null) {
  $MSVC_INSTALL_DIR = "C:\Program Files (x86)\Microsoft Visual Studio"
  if (-not (Test-Path -PathType Container -Path "${MSVC_INSTALL_DIR}")) {
    $MSVC_INSTALL_DIR = "C:\Program Files\Microsoft Visual Studio"
  }
}
$MSVC_SKIP_AUTO_SEARCH = ${env:MSVC_SKIP_AUTO_SEARCH}
if ($MSVC_SKIP_AUTO_SEARCH -eq $null) {
  $MSVC_SKIP_AUTO_SEARCH = "0"
}
if ($MSVC_SKIP_AUTO_SEARCH -ieq "0") {
  $VS_SEARCH_PATH = @(
    "${MSVC_INSTALL_DIR}\2022\BuildTools",
    "${MSVC_INSTALL_DIR}\2022\Community",
    "${MSVC_INSTALL_DIR}\2022\Professional",
    "${MSVC_INSTALL_DIR}\2022\Enterprise",
    "${MSVC_INSTALL_DIR}\2019\BuildTools",
    "${MSVC_INSTALL_DIR}\2019\Community",
    "${MSVC_INSTALL_DIR}\2019\Professional",
    "${MSVC_INSTALL_DIR}\2019\Enterprise"
  )
} else {
  $VS_SEARCH_PATH = @( "${MSVC_INSTALL_DIR}" )
}

$vs_devshell_ok = $false
foreach ($VS_PATH in $VS_SEARCH_PATH) {
  $vs_devshell_ok = vsdevsh "$VS_PATH"
  if ($vs_devshell_ok) { break }
}
if (-not $vs_devshell_ok) { exit 1 }
# <<< VS DevShell <<<
