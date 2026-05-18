param(
    [string]$ConfigPath = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
    $ConfigPath = Join-Path $PSScriptRoot "windows_agent_config.json"
}

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    throw "Konfigurationsdatei nicht gefunden: $ConfigPath"
}

$config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json

if (-not $config.repo_root) {
    throw "repo_root fehlt in der Konfiguration."
}
if (-not $config.python_executable) {
    throw "python_executable fehlt in der Konfiguration."
}

$env:SERVER_URL = [string]$config.server_url
$env:SERVER_API_KEY = [string]$config.api_key
$env:AGENT_INTERVAL_SECONDS = [string]$config.interval_seconds
$env:CLIENT_ID_FILE = Join-Path ([string]$config.repo_root) ".client_id"

Set-Location -LiteralPath ([string]$config.repo_root)
& ([string]$config.python_executable) -m client.agent
