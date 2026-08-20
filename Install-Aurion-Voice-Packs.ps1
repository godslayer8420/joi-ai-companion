# Register Windows TTS Voice Packs for Aurion
# Script: Install-Aurion-Voice-Packs.ps1
# Purpose: Register Aria and Jenny Windows voice packs as system TTS voices
# Usage: Run as Administrator in PowerShell (or PowerShell ISE)
#   PS C:\> .\Install-Aurion-Voice-Packs.ps1
# 
# These voice packs will be available to Aurion for Text-to-Speech (TTS) output.
# After installation, use Aurion voice aliases: "aria", "jenny", "aria-tts", "jenny-tts"

#Requires -RunAsAdministrator

param(
    [string]$AriaPath = "D:\Downloads\Others\MicrosoftWindows.Voice.en-US.Aria.2_1.0.1.0_x64__cw5n1h2txyewy.Msix",
    [string]$JennyPath = "D:\Downloads\Others\MicrosoftWindows.Voice.en-US.Jenny.2_1.0.1.0_x64__cw5n1h2txyewy.Msix",
    [switch]$WhatIf
)

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "  Aurion Voice Pack Installation" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

# Check admin rights
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "❌ This script must run as Administrator." -ForegroundColor Red
    Write-Host "   Please run PowerShell as Administrator and try again." -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Running as Administrator" -ForegroundColor Green
Write-Host ""

# Validate paths
$MissingFiles = @()

if (-not (Test-Path $AriaPath)) {
    $MissingFiles += "Aria: $AriaPath"
} else {
    Write-Host "✓ Aria path found: $AriaPath" -ForegroundColor Green
}

if (-not (Test-Path $JennyPath)) {
    $MissingFiles += "Jenny: $JennyPath"
} else {
    Write-Host "✓ Jenny path found: $JennyPath" -ForegroundColor Green
}

if ($MissingFiles.Count -gt 0) {
    Write-Host ""
    Write-Host "❌ Missing voice pack files:" -ForegroundColor Red
    foreach ($file in $MissingFiles) {
        Write-Host "   - $file" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "   Download these files to D:\Downloads\Others\ or modify the -AriaPath / -JennyPath parameters." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Installing voice packs..." -ForegroundColor Cyan
Write-Host ""

try {
    # Install Aria voice pack
    Write-Host "📦 Installing Aria TTS voice pack..." -ForegroundColor Cyan
    if ($WhatIf) {
        Write-Host "   [WhatIf] Would run: Add-AppxPackage -Path `"$AriaPath`"" -ForegroundColor Yellow
    } else {
        Add-AppxPackage -Path $AriaPath -ErrorAction Stop
        Write-Host "   ✓ Aria installed successfully" -ForegroundColor Green
    }

    Write-Host ""

    # Install Jenny voice pack
    Write-Host "📦 Installing Jenny TTS voice pack..." -ForegroundColor Cyan
    if ($WhatIf) {
        Write-Host "   [WhatIf] Would run: Add-AppxPackage -Path `"$JennyPath`"" -ForegroundColor Yellow
    } else {
        Add-AppxPackage -Path $JennyPath -ErrorAction Stop
        Write-Host "   ✓ Jenny installed successfully" -ForegroundColor Green
    }

    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
    Write-Host "  ✓ All voice packs installed successfully!" -ForegroundColor Green
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
    Write-Host ""
    Write-Host "Aurion can now use these voices:" -ForegroundColor Cyan
    Write-Host "  • Alias 'aria' or 'aria-tts' → Aria TTS voice" -ForegroundColor White
    Write-Host "  • Alias 'jenny' or 'jenny-tts' → Jenny TTS voice" -ForegroundColor White
    Write-Host ""
    Write-Host "Set voice in Aurion via environment variable:" -ForegroundColor Cyan
    Write-Host "  Set-Item -Path Env:AURION_VOICE_MODEL -Value 'aria'" -ForegroundColor Yellow
    Write-Host "  Set-Item -Path Env:AURION_VOICE_MODEL -Value 'jenny'" -ForegroundColor Yellow
    Write-Host ""

} catch {
    Write-Host ""
    Write-Host "❌ Installation failed:" -ForegroundColor Red
    Write-Host "   $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Common causes:" -ForegroundColor Yellow
    Write-Host "  • MSIX files are corrupted or incomplete" -ForegroundColor Gray
    Write-Host "  • Voice pack is already installed" -ForegroundColor Gray
    Write-Host "  • System policy blocks app installation" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

exit 0
