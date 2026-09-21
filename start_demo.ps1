$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$CustomerUrl = "http://localhost:8501"
$AdminUrl = "http://localhost:8502"

if (-not (Test-Path $Python)) {
    Write-Error "Python environment not found at $Python. Run the setup steps in AI_LAB_HANDOFF.md first."
}

function Test-PortFree([int] $Port) {
    return -not (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Wait-ForPort([int] $Port, [int] $TimeoutSeconds = 30) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (-not (Test-PortFree $Port)) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

foreach ($Port in @(8501, 8502)) {
    if (-not (Test-PortFree $Port)) {
        Write-Warning "Port $Port is already in use. The existing service will be kept running."
    }
}

if (Test-PortFree 8501) {
    Start-Process powershell.exe -ArgumentList @(
        "-NoExit", "-ExecutionPolicy", "Bypass", "-Command",
        "& '$Python' -m streamlit run '$Root\app.py' --server.port 8501"
    )
}

if (Test-PortFree 8502) {
    Start-Process powershell.exe -ArgumentList @(
        "-NoExit", "-ExecutionPolicy", "Bypass", "-Command",
        "& '$Python' -m streamlit run '$Root\admin_dashboard.py' --server.port 8502"
    )
}

if (-not (Wait-ForPort 8501) -or -not (Wait-ForPort 8502)) {
    throw "A Streamlit service did not start within 30 seconds. Check the server windows for the startup error."
}

Start-Process $CustomerUrl
Start-Process $AdminUrl
Write-Host "Customer portal: $CustomerUrl"
Write-Host "Admin console:   $AdminUrl"
Write-Host "Close the two Streamlit windows to stop the demo."