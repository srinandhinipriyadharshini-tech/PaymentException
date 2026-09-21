param(
    [switch] $SkipInstall
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$CustomerUrl = "http://localhost:8501"
$AdminUrl = "http://localhost:8502"
$Requirements = Join-Path $Root "requirements.txt"
$Database = Join-Path $Root "data\payment_exceptions.duckdb"

function Invoke-Python([string[]] $Arguments) {
    & $Python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed: $($Arguments -join ' ')"
    }
}

function Find-Python {
    $pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pythonLauncher) {
        $null = & py -3.14 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            return "py -3.14"
        }
    }
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        return $pythonCommand.Source
    }
    throw "Python 3.14 was not found. Install Python from https://www.python.org/downloads/windows/ and run this script again."
}

if (-not (Test-Path $Python)) {
    $BootstrapPython = Find-Python
    Write-Host "Creating Python environment..." -ForegroundColor Cyan
    if ($BootstrapPython -eq "py -3.14") {
        & py -3.14 -m venv $Root\.venv
    } else {
        & $BootstrapPython -m venv $Root\.venv
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create .venv. Check that Python is installed and available in PowerShell."
    }
}

if (-not $SkipInstall) {
    Write-Host "Installing Python packages..." -ForegroundColor Cyan
    Invoke-Python @("-m", "pip", "install", "--disable-pip-version-check", "-r", $Requirements)
}

if (-not (Test-Path $Database)) {
    Write-Host "Creating the synthetic payment database..." -ForegroundColor Cyan
    Invoke-Python @("data\create_database.py")
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
Write-Host "For future launches, use: .\start_demo.ps1 -SkipInstall" -ForegroundColor DarkGray