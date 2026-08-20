# Find and Start Local JupyterLab for Aurion Quantum Brain
# Script: Start-Aurion-Jupyter.ps1
# Purpose: Locate Python/Jupyter on disk (WSL, native Windows, or virtual env)
#          and start JupyterLab for Ouroboros + OpenmythoS quantum memory layer
# Usage: Run in PowerShell
#   PS C:\> .\Start-Aurion-Jupyter.ps1
#   PS C:\> .\Start-Aurion-Jupyter.ps1 -Port 8888 -NoAutoOpen
#
# This launches JupyterLab on localhost:{port} for free-first provider hierarchy.
# Once running, set: $env:AURION_CUSTOM_LOCAL_BASE_URL = "http://localhost:8888"

param(
    [int]$Port = 8888,
    [switch]$NoAutoOpen,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "  Aurion Quantum Brain — JupyterLab Launcher" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

# Candidate locations for Python/Jupyter
$searchPaths = @(
    "D:\bzimm\.venv\Scripts\jupyter.exe",
    "D:\bzimm\.local\bin\jupyter",
    "C:\Python311\Scripts\jupyter.exe",
    "C:\Python310\Scripts\jupyter.exe",
    "C:\Users\bzimm\AppData\Local\Programs\Python\Python311\Scripts\jupyter.exe"
)

$jupyterFound = $null

Write-Host "Scanning for Python/Jupyter installation..." -ForegroundColor Cyan
Write-Host ""

foreach ($path in $searchPaths) {
    if (Test-Path $path) {
        Write-Host "✓ Found: $path" -ForegroundColor Green
        $jupyterFound = $path
        break
    }
}

if (-not $jupyterFound) {
    Write-Host "Checking for WSL (Ubuntu/Debian)..." -ForegroundColor Cyan
    
    # Check if WSL is available
    if (Get-Command wsl -ErrorAction SilentlyContinue) {
        Write-Host "✓ WSL is installed" -ForegroundColor Green
        Write-Host ""
        
        # Try to start Jupyter via WSL
        Write-Host "Attempting to start JupyterLab via WSL..." -ForegroundColor Cyan
        Write-Host ""
        
        if ($DryRun) {
            Write-Host "[DryRun] Would execute:" -ForegroundColor Yellow
            Write-Host "  wsl jupyter lab --no-browser --port=$Port" -ForegroundColor Gray
        } else {
            try {
                Write-Host "Starting: wsl jupyter lab --no-browser --port=$Port" -ForegroundColor White
                Write-Host ""
                Write-Host "Access JupyterLab at: http://localhost:$Port" -ForegroundColor Green
                Write-Host ""
                
                & wsl jupyter lab --no-browser --port=$Port
                
            } catch {
                Write-Host ""
                Write-Host "❌ Failed to start JupyterLab: $_" -ForegroundColor Red
                Write-Host ""
                Write-Host "Common fixes:" -ForegroundColor Yellow
                Write-Host "  1. Install Jupyter in WSL: wsl pip install jupyterlab" -ForegroundColor Gray
                Write-Host "  2. Ensure Python 3.8+ is installed: wsl python --version" -ForegroundColor Gray
                exit 1
            }
        }
    } else {
        Write-Host "❌ WSL not found, and no native Python/Jupyter detected" -ForegroundColor Red
        Write-Host ""
        Write-Host "Install options:" -ForegroundColor Yellow
        Write-Host "  Option 1: Install WSL + Python" -ForegroundColor White
        Write-Host "    wsl --install -d Ubuntu" -ForegroundColor Gray
        Write-Host "    wsl pip install jupyterlab" -ForegroundColor Gray
        Write-Host ""
        Write-Host "  Option 2: Install Python 3.11 from python.org, then:" -ForegroundColor White
        Write-Host "    pip install jupyterlab" -ForegroundColor Gray
        Write-Host ""
        exit 1
    }
    
} else {
    # Found native Jupyter
    Write-Host ""
    Write-Host "Starting JupyterLab from: $jupyterFound" -ForegroundColor Cyan
    Write-Host ""
    
    if ($DryRun) {
        Write-Host "[DryRun] Would execute:" -ForegroundColor Yellow
        Write-Host "  & `"$jupyterFound`" lab --no-browser --port=$Port" -ForegroundColor Gray
    } else {
        try {
            Write-Host "Launching JupyterLab on port $Port..." -ForegroundColor White
            Write-Host "Access at: http://localhost:$Port" -ForegroundColor Green
            Write-Host ""
            
            & $jupyterFound lab --no-browser --port=$Port
            
        } catch {
            Write-Host ""
            Write-Host "❌ Failed to start JupyterLab: $_" -ForegroundColor Red
            exit 1
        }
    }
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "  ✓ JupyterLab is running!" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Open browser: http://localhost:$Port" -ForegroundColor White
Write-Host "  2. Navigate to: ai_core/ouroboros/" -ForegroundColor White
Write-Host "  3. Load: ouroboros-main/notebooks/" -ForegroundColor White
Write-Host "  4. In new PowerShell, set environment and test:" -ForegroundColor White
Write-Host "     \`$env:AURION_CUSTOM_LOCAL_BASE_URL = `"http://localhost:$Port`"" -ForegroundColor Yellow
Write-Host "     python joi_companion/web_ui.py" -ForegroundColor Yellow
Write-Host ""

exit 0
