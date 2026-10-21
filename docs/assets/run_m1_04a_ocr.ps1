# Runs dots.mocr (OCR-Lab, Docker) on the M1-04A check-pool batch and writes
# immutable outputs under data/m1/m1-04a/ocr/<slug>/run-01[/logical-text] plus
# a saved-results replay in run-01-replay. Run from the repository root:
#   powershell -File docs/assets/run_m1_04a_ocr.ps1
# Existing run folders are never overwritten: such acts are skipped.
param(
    [string]$Batch = "batch-01",
    [string]$Experiment = "20261021-batch-01-ocr",
    [string]$LabRoot = "H:/AI_AGENT/OCR-Lab",
    [string[]]$Slugs = @("fz-22-2018", "fz-23-2018", "pp-1455-2022", "pp-884-2024",
        "prikaz-minobrazovaniya-901-2015", "prikaz-mintsifrovogo-173-2021",
        "rp-1378-2018", "ukaz-204-2016"),
    [int]$HealthTimeoutSeconds = 600,
    [switch]$ReplayOnly   # skip Docker/extraction; only replay saved results
)
$ErrorActionPreference = "Stop"
$env:PYTHONPATH = "src"
$python = ".venv\Scripts\python.exe"
$base = "data/m1/m1-04a"
$experimentDir = "$base/experiments/$Experiment"
New-Item -ItemType Directory -Force -Path $experimentDir | Out-Null

$summary = [ordered]@{ acts = [ordered]@{} }
function Save-Json($value, $path) {
    [IO.File]::WriteAllText((Join-Path (Get-Location) $path), ($value | ConvertTo-Json -Depth 20), (New-Object Text.UTF8Encoding($false)))
}
if (-not $ReplayOnly) {
# 1. GPU must be free enough for dots.mocr (it reserves 65% of memory).
$gpu = (nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits).Trim() -split ",\s*"
$usedMiB = [int]$gpu[0]; $totalMiB = [int]$gpu[1]
Write-Host "GPU memory used: $usedMiB / $totalMiB MiB"
$others = docker ps --filter "name=ocr-lab-" --format "{{.Names}}" | Where-Object { $_ -ne "ocr-lab-dotsmocr" }
if ($others) { throw "Other OCR-Lab containers hold the GPU: $others" }
if ($usedMiB -gt 0.5 * $totalMiB) { throw "GPU is busy: $usedMiB MiB in use" }

# 2. Start the service and wait for health (max 10 minutes), else fail before extraction.
$clock = [Diagnostics.Stopwatch]::StartNew()
docker compose --project-directory $LabRoot up -d dotsmocr
if ($LASTEXITCODE) { throw "docker compose up failed" }
$healthy = $false
while ($clock.Elapsed.TotalSeconds -lt $HealthTimeoutSeconds) {
    $state = docker inspect --format "{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}" ocr-lab-dotsmocr
    if ($state.Trim() -eq "running healthy") { $healthy = $true; break }
    Start-Sleep -Seconds 10
}
$healthWait = [math]::Round($clock.Elapsed.TotalSeconds, 1)
if (-not $healthy) { throw "dotsmocr not healthy after $healthWait s (last state: $state)" }
Write-Host "dotsmocr healthy after $healthWait s"

$summary.health_wait_seconds = $healthWait
try {
    foreach ($slug in $Slugs) {
        $inputJson = "$base/documents/pool/$Batch/$slug/input.json"
        $run = "$base/ocr/$slug/run-01"
        if (Test-Path $run) { Write-Host "skip $slug (run-01 exists)"; continue }
        $watch = [Diagnostics.Stopwatch]::StartNew()
        $out = & $python -m legal_rag.corpus extract --input $inputJson --ocr-config data/m1/ocr.local.json --output-dir $run
        if ($LASTEXITCODE) { $summary.acts[$slug] = @{ status = "failed" }; Write-Host "FAILED $slug"; continue }
        $seconds = [math]::Round($watch.Elapsed.TotalSeconds, 1)
        $result = ($out | Select-Object -Last 1) | ConvertFrom-Json
        Save-Json $result "$base/ocr/$slug/run-01-extract-result.json"
        $digest = @($result.extractions.PSObject.Properties.Name)[0]
        $entry = $result.extractions.$digest
        $extraction = "$run/extractions/$($entry.path)"
        & $python -m legal_rag.corpus logical-text --extraction $extraction --output-dir $run
        if ($LASTEXITCODE) { throw "logical-text failed for $slug" }
        $summary.acts[$slug] = [ordered]@{
            status = "complete"; seconds = $seconds; source_asset_sha256 = $digest
            extraction_id = $entry.extraction_id; extraction = $extraction
            native_evidence = $result.native_evidence.$digest
        }
    }
} finally {
    docker compose --project-directory $LabRoot stop dotsmocr
}

}

# 3. Replay saved native results (no Docker needed) and compare extraction ids.
$replays = [ordered]@{}
foreach ($slug in $Slugs) {
    $resultFile = "$base/ocr/$slug/run-01-extract-result.json"
    $replay = "$base/ocr/$slug/run-01-replay"
    if (-not (Test-Path $resultFile) -or (Test-Path $replay)) { continue }
    $first = Get-Content -Raw -Encoding utf8 $resultFile | ConvertFrom-Json
    $digest = @($first.extractions.PSObject.Properties.Name)[0]
    $evidence = Split-Path $first.native_evidence.$digest -Leaf
    $map = "$base/ocr/$slug/run-01-results.json"
    Save-Json @{ schema_version = "ocr-results/1"; results = @{ $digest = "run-01/ocr-evidence/$evidence" } } $map
    $out = & $python -m legal_rag.corpus extract --input "$base/documents/pool/$Batch/$slug/input.json" --ocr-results $map --output-dir $replay
    if ($LASTEXITCODE) { $replays[$slug] = @{ replay_match = $false }; continue }
    $again = ($out | Select-Object -Last 1) | ConvertFrom-Json
    $replayId = $again.extractions.$digest.extraction_id
    $replays[$slug] = [ordered]@{ replay_extraction_id = $replayId; replay_match = ($replayId -eq $first.extractions.$digest.extraction_id) }
}
$summary.replays = $replays
# A replay-only pass never overwrites the raw summary of an earlier pass.
$rawName = if ($ReplayOnly) { "summary.raw.replay-$((Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')).json" } else { "summary.raw.json" }
if (Test-Path "$experimentDir/$rawName") { throw "$experimentDir/$rawName exists; not overwritten" }
Save-Json $summary "$experimentDir/$rawName"
Write-Host "done; raw summary in $experimentDir/$rawName (per-act summary: docs/assets/summarize_m1_04a_ocr.py)"
