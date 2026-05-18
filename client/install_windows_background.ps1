param(
    [Parameter(Mandatory = $true)]
    [string]$ServerUrl,
    [Parameter(Mandatory = $true)]
    [string]$ApiKey,
    [int]$IntervalSeconds = 60,
    [string]$TaskName = "HardwareMonitorClientAgent",
    [switch]$StartNow
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$venvRoot = Join-Path $repoRoot ".venv"
$venvPython = Join-Path $venvRoot "Scripts\python.exe"
$requirementsPath = Join-Path $repoRoot "requirements.txt"

function Resolve-PythonExecutable {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        return @($pythonCommand.Source)
    }

    $pyCommand = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCommand) {
        return @($pyCommand.Source, "-3")
    }

    throw "Python nicht gefunden. Bitte zuerst Python 3 installieren."
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host "Erstelle virtuelle Umgebung..." -ForegroundColor Cyan
    $pythonInvocation = @(Resolve-PythonExecutable)
    if ($pythonInvocation.Count -gt 1) {
        $pythonArgs = @($pythonInvocation[1..($pythonInvocation.Count - 1)] + @("-m", "venv", $venvRoot))
        & $pythonInvocation[0] @pythonArgs
    } else {
        & $pythonInvocation[0] -m venv $venvRoot
    }
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Virtuelle Umgebung konnte nicht erstellt werden."
}

$pythonExecutable = $venvPython

Write-Host "Installiere/aktualisiere Python-Abhängigkeiten..." -ForegroundColor Cyan
& $pythonExecutable -m pip install --upgrade pip | Out-Null
& $pythonExecutable -m pip install -r $requirementsPath

$configPath = Join-Path $PSScriptRoot "windows_agent_config.json"
$runnerPath = Join-Path $PSScriptRoot "windows_agent_runner.ps1"

$config = [ordered]@{
    repo_root = [string]$repoRoot
    python_executable = [string]$pythonExecutable
    server_url = $ServerUrl
    api_key = $ApiKey
    interval_seconds = $IntervalSeconds
}

$config | ConvertTo-Json | Set-Content -LiteralPath $configPath -Encoding UTF8

$taskArgument = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$runnerPath`" -ConfigPath `"$configPath`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $taskArgument -WorkingDirectory ([string]$repoRoot)
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null

if ($StartNow) {
    Start-ScheduledTask -TaskName $TaskName
}

Write-Host "Hintergrunddienst eingerichtet." -ForegroundColor Green
Write-Host "Task-Name: $TaskName"
Write-Host "Konfiguration: $configPath"
Write-Host "Server URL: $ServerUrl"
Write-Host "Intervall: $IntervalSeconds Sekunden"
Write-Host ""
Write-Host "Zum manuellen Start:" -ForegroundColor Yellow
Write-Host "Start-ScheduledTask -TaskName `"$TaskName`""
Write-Host "Zum Entfernen:" -ForegroundColor Yellow
Write-Host "Unregister-ScheduledTask -TaskName `"$TaskName`" -Confirm:`$false"
