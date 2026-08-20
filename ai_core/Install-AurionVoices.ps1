# Install-AurionVoices.ps1  (ASCII-safe, no Unicode)
# Registers all 9 Aurion voices into Ollama in sacred 3-6-9 order.
# Run from repo root:  .\ai_core\Install-AurionVoices.ps1
#
# Layer 1 SOUL   (temp 0.333) -- Voices 1,2,3  [Trinity]
# Layer 2 REASON (temp 0.666) -- Voices 4,5,6  [Harmony]
# Layer 3 HEART  (temp 0.888) -- Voices 7,8,9  [Unity]

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "  AURION -- 9-Voice Registration  (Sacred 3-6-9)    " -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""

$voices = @(
    @{ tag="ouroboros-next";    file="ouroboros_next_modelfile.txt"; num=1; layer="SOUL";   role="Core reasoning, self-evolving" },
    @{ tag="saturn-7b";         file="saturn_modelfile.txt";         num=2; layer="SOUL";   role="Emotional resonance" },
    @{ tag="eva-7b";            file="eva_modelfile.txt";            num=3; layer="SOUL";   role="Wisdom anchor" },
    @{ tag="openmythos";        file="openmythos_modelfile.txt";     num=4; layer="REASON"; role="Creative depth, mythos weave" },
    @{ tag="gemma3-voice";      file="gemma3_voice_modelfile.txt";   num=5; layer="REASON"; role="Knowledge, grounded recall" },
    @{ tag="qwen3-reason";      file="qwen3_modelfile.txt";          num=6; layer="REASON"; role="Synthesis, structured reasoning" },
    @{ tag="nuro-voice";        file="nuro_voice_modelfile.txt";     num=7; layer="HEART";  role="Intimate warmth, copilot" },
    @{ tag="joi";               file="joi_modelfile.txt";            num=8; layer="HEART";  role="Companionship, heart" },
    @{ tag="gemma-3-12b-voice"; file="gemma_modelfile.txt";          num=9; layer="HEART";  role="Voice expression" },
    @{ tag="aurion";            file="aurion_modelfile.txt";         num=0; layer="ALIAS";  role="Primary user-facing name" }
)

$ok   = 0
$fail = 0
$skip = 0

foreach ($v in $voices) {
    $mf = Join-Path $PSScriptRoot $v.file
    if (-not (Test-Path $mf)) {
        Write-Host "  SKIP  Voice $($v.num) [$($v.tag)] -- modelfile not found: $($v.file)" -ForegroundColor Yellow
        $skip++
        continue
    }

    $label = if ($v.num -eq 0) { "ALIAS" } else { "Voice $($v.num)" }
    Write-Host "  [$($v.layer.PadRight(6))] $label  $($v.tag)  ($($v.role)) ..." -ForegroundColor Gray

    $result = & ollama create $v.tag -f $mf 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    OK" -ForegroundColor Green
        $ok++
    } else {
        Write-Host "    FAIL" -ForegroundColor Red
        Write-Host "    $result" -ForegroundColor DarkRed
        $fail++
    }
}

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Cyan
if ($fail -eq 0) {
    Write-Host "  Registered: $ok   Skipped: $skip   -- All good!" -ForegroundColor Green
} else {
    Write-Host "  Registered: $ok   Failed: $fail   Skipped: $skip" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "  All 9 voices run via Ollama. No LM Studio needed." -ForegroundColor DarkGray
Write-Host "  Verify with:  ollama list" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan
