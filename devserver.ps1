# PowerShell dev server script for Windows
param(
    [int]$Port = 8080
)

$venvActivate = ".\.venv\Scripts\Activate.ps1"

if (Test-Path $venvActivate) {
    Write-Host "Activating virtual environment..."
    . $venvActivate
} else {
    Write-Host ".venv not found. Creating virtual environment..."
    python -m venv .venv
    if (-Not (Test-Path $venvActivate)) {
        Write-Error "Failed to create virtualenv or activate script missing."
        exit 1
    }
    . $venvActivate
    if (Test-Path "requirements.txt") {
        Write-Host "Installing dependencies from requirements.txt..."
        python -m pip install --upgrade pip
        python -m pip install -r requirements.txt
    }
}

if (-not $env:FLASK_APP) {
    if (Test-Path ".\app.py") { $env:FLASK_APP = "app.py" }
    elseif (Test-Path ".\main.py") { $env:FLASK_APP = "main.py" }
}

Write-Host "Starting Flask on 0.0.0.0:$Port"
python -m flask run --host=0.0.0.0 --port=$Port
