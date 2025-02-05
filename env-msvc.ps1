param (
  [Parameter(Mandatory=$true)][string]${private:TARGET_ARCH}
)

$PARALLEL_JOBS = ${env:NUMBER_OF_PROCESSORS}

${private:ccache} = Get-Command -Name ccache.exe -CommandType Application -ErrorAction SilentlyContinue
if (${private:ccache} -ne $null) {
  ${CCACHE_SRC} = "ccache.exe"

  # https://github.com/ccache/ccache/discussions/978
  ${CMAKE_EXTRA} = "${CMAKE_EXTRA} -D CMAKE_C_COMPILER_LAUNCHER=ccache.exe ``
    -D CMAKE_CXX_COMPILER_LAUNCHER=ccache.exe"
}

# >>> VS DevShell >>>
# Only supports access to the VS DevShell from PowerShell
# see https://learn.microsoft.com/visualstudio/ide/reference/command-prompt-powershell#developer-powershell
$HOST_ARCH = ${env:PROCESSOR_ARCHITECTURE}.ToLower()

# Alreay accessed the VS DevShell
${private:_VSCMD_ARG_TGT_ARCH} = ${env:VSCMD_ARG_TGT_ARCH}
if (${_VSCMD_ARG_TGT_ARCH} -ne $null) {
  if (${_VSCMD_ARG_TGT_ARCH} -ieq "x64") {
    ${_VSCMD_ARG_TGT_ARCH} = "amd64"
  }
  if (${_VSCMD_ARG_TGT_ARCH} -ieq ${TARGET_ARCH}) {
    exit 0
  }
}

function vsdevsh {
  param (
    [Parameter(Mandatory=$true)][string]${private:VS_PATH},
    [Parameter(Mandatory=$true)][string]${private:TARGET_ARCH}
  )

  ${private:VS_DEVCMD_ARGS} = "-host_arch=${HOST_ARCH} -arch=${TARGET_ARCH}"
  ${private:VS_PS1} = "${VS_PATH}\Common7\Tools\Microsoft.VisualStudio.DevShell.dll"
  if (-not (Test-Path -PathType Leaf -Path "${VS_PS1}")) {
    return $false
  }
  Write-Host -ForegroundColor Green "Enter VS DevShell via PS1: `
    `r`n  ${VS_PS1} `r`n  DevCmdArguments: '${VS_DEVCMD_ARGS}' `r`n"
  Import-Module "${VS_PS1}"
  Enter-VsDevShell -VsInstallPath "${VS_PATH}" -SkipAutomaticLocation -DevCmdArguments "${VS_DEVCMD_ARGS}"
  return $true
}

# Set VS search path
${private:MSVC_INSTALL_DIR_64BIT}="C:\Program Files\Microsoft Visual Studio"
${private:MSVC_INSTALL_DIR_32BIT}="C:\Program Files (x86)\Microsoft Visual Studio"

${private:VS_SEARCH_PATH} = @( "${env:MSVC_INSTALL_DIR}" )
if ((${env:MSVC_SKIP_AUTO_SEARCH} -eq $null) -or (${env:MSVC_SKIP_AUTO_SEARCH} -ieq "0")) {
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
}

$vs_devshell_ok = $false
foreach ($VS_PATH in $VS_SEARCH_PATH) {
  $vs_devshell_ok = vsdevsh "$VS_PATH" "$TARGET_ARCH"
  if ($vs_devshell_ok) { break }
}
if (-not $vs_devshell_ok) {
  Write-Error -Message "Failed to search MSVC environment."
  exit 1
}
# <<< VS DevShell <<<
