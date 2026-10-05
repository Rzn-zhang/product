$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (Get-Command python -ErrorAction SilentlyContinue) {
    & python server.py
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 server.py
} else {
    throw 'Python 3.10 or later is required. Install Python and add it to PATH.'
}
