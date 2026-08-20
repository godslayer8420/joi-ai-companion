# Setup Ollama Voice Models for Aurion
# Script: Initialize-Aurion-Voice-Models.ps1
# Purpose: Create and load all voice models in Ollama from Modelfiles
# Usage: Run in PowerShell (Ollama must be running: http://localhost:11434)
#   PS C:\> .\Initialize-Aurion-Voice-Models.ps1
#
# This script creates Ollama models from the Modelfiles for:
#   - nuro-voice (Nuro Copilot 7B voice model)
#   - gemma-3-12b-voice (Gemma 3 12B voice assistant)
#
# After setup, use Aurion voice model aliases:
#   "nuro-voice", "aurion-voice", "gemma-3-voice", "gemma-voice"

param(
    [string]$OllamaUrl = "http://localhost:11434",
    [string]$RepoRoot = "D:\bzimm\GitHub Copilot\copilot-worktrees\joi-ai-companion\godslayer8420-fuzzy-meme",
    [switch]$Force,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Write-Status {
    param([string]$Message, [string]$Status = "Info")
    
    $colors = @{
        "Success" = [ConsoleColor]::Green
        "Error" = [ConsoleColor]::Red
        "Warning" = [ConsoleColor]::Yellow
        "Info" = [ConsoleColor]::Cyan
    }
    
    $color = $colors[$Status] ?? [ConsoleColor]::White
    Write-Host "[$Status] $Message" -ForegroundColor $color
}

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "  Aurion Voice Models Setup" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

# Check Ollama is running
Write-Status "Checking Ollama connection at $OllamaUrl..." "Info"
try {
    $response = Invoke-RestMethod -Uri "$OllamaUrl/api/tags" -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Status "✓ Ollama is running" "Success"
    Write-Host ""
} catch {
    Write-Status "❌ Cannot connect to Ollama at $OllamaUrl" "Error"
    Write-Host "Make sure Ollama is running:" -ForegroundColor Yellow
    Write-Host "  ollama serve" -ForegroundColor Gray
    exit 1
}

# Define models to create
$models = @(
    @{
        Name = "nuro-voice"
        Modelfile = "ai_core/nuro_voice_modelfile.txt"
        Description = "Nuro Copilot 7B Voice Model"
    },
    @{
        Name = "gemma-3-12b-voice"
        Modelfile = "ai_core/gemma3_voice_modelfile.txt"
        Description = "Gemma 3 12B Voice Assistant"
    }
)

# Create models
foreach ($model in $models) {
    Write-Status "Setting up: $($model.Description)" "Info"
    
    $modelfilePath = Join-Path $RepoRoot $model.Modelfile
    
    if (-not (Test-Path $modelfilePath)) {
        Write-Status "  ❌ Modelfile not found: $modelfilePath" "Error"
        continue
    }
    
    Write-Status "  • Modelfile: $modelfilePath" "Info"
    
    # Read Modelfile
    $modelfileContent = Get-Content -Path $modelfilePath -Raw
    
    # Check if model already exists
    Write-Status "  • Checking if model '$($model.Name)' already exists..." "Info"
    $existingModels = $response.models | Where-Object { $_.name -eq $model.Name }
    
    if ($existingModels -and -not $Force) {
        Write-Status "  • Model '$($model.Name)' already exists. Use -Force to recreate." "Warning"
        Write-Host ""
        continue
    }
    
    if ($DryRun) {
        Write-Status "  [DryRun] Would create model: $($model.Name)" "Info"
        Write-Host "  Modelfile content:" -ForegroundColor Gray
        foreach ($line in $modelfileContent -split "`n" | Select-Object -First 5) {
            Write-Host "    $line" -ForegroundColor Gray
        }
        Write-Host "    ..." -ForegroundColor Gray
        Write-Host ""
        continue
    }
    
    # Create model using ollama CLI
    Write-Status "  • Creating model: $($model.Name)..." "Info"
    try {
        & ollama create $model.Name -f $modelfilePath 2>&1 | ForEach-Object { 
            Write-Host "    $_" -ForegroundColor Gray 
        }
        Write-Status "  ✓ Model '$($model.Name)' created successfully" "Success"
    } catch {
        Write-Status "  ❌ Failed to create model: $_" "Error"
        continue
    }
    
    Write-Host ""
}

# Verify models
Write-Host ""
Write-Status "Verifying installed models..." "Info"
try {
    $response = Invoke-RestMethod -Uri "$OllamaUrl/api/tags" -Method GET -TimeoutSec 5
    $voiceModels = $response.models | Where-Object { 
        $_.name -match "voice|nuro|gemma-3-12b-voice"
    }
    
    if ($voiceModels) {
        Write-Host ""
        Write-Host "✓ Voice models available:" -ForegroundColor Green
        foreach ($vm in $voiceModels) {
            Write-Host "  • $($vm.name)" -ForegroundColor Green
        }
    } else {
        Write-Host ""
        Write-Host "⚠ No voice models found. Check Ollama logs." -ForegroundColor Yellow
    }
} catch {
    Write-Status "Could not verify models: $_" "Warning"
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Run: .\Install-Aurion-Voice-Packs.ps1 (as Administrator)" -ForegroundColor White
Write-Host "  2. Set environment variable:" -ForegroundColor White
Write-Host "     \`$env:AURION_VOICE_MODEL = 'nuro-voice'" -ForegroundColor Yellow
Write-Host "  3. Start Aurion and test voice interaction" -ForegroundColor White
Write-Host ""

exit 0
