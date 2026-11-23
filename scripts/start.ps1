Param(
    [switch]$NoDashboard,
    [switch]$KeepOpen
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
$python = (Resolve-Path ".\.venv\Scripts\python.exe").Path
& $python -m pip install -r requirements.txt
& $python -c "from app.database import init_db; init_db()"

New-Item -ItemType Directory -Force .logs | Out-Null
$apiArgs = "-m uvicorn app.api.main:app --host 127.0.0.1 --port 8000"
$api = Start-Process $python -ArgumentList $apiArgs -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput ".\logs\api.log" -RedirectStandardError ".\logs\api.err.log"

$dashboard = $null
if (-not $NoDashboard) {
    $dashboardArgs = "-m streamlit run app/dashboard/app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats=false"
    $dashboard = Start-Process $python -ArgumentList $dashboardArgs -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput ".\logs\dashboard.log" -RedirectStandardError ".\logs\dashboard.err.log"
}

Write-Host "API: http://127.0.0.1:8000"
Write-Host "Dashboard: http://127.0.0.1:8501"

$deadline = (Get-Date).AddSeconds(30)
do {
    Start-Sleep -Milliseconds 500
    try {
        $apiReady = (Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:8000/health).StatusCode -eq 200
    } catch {
        $apiReady = $false
    }
    if ($apiReady) { break }
} while ((Get-Date) -lt $deadline)

if (-not $apiReady) {
    Write-Error "API failed to start. See logs\api.err.log"
}

if (-not $NoDashboard) {
    $dashboardDeadline = (Get-Date).AddSeconds(30)
    do {
        Start-Sleep -Milliseconds 500
        try {
            $dashboardReady = (Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:8501).StatusCode -eq 200
        } catch {
            $dashboardReady = $false
        }
        if ($dashboardReady) { break }
    } while ((Get-Date) -lt $dashboardDeadline)

    if (-not $dashboardReady) {
        Write-Error "Dashboard failed to start. See logs\dashboard.err.log"
    }
}
