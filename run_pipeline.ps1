# =============================================================================
# Legends Sports — Pipeline PowerShell Runner
# =============================================================================
# Windows Task Scheduler bu dosyayi calistirir.
# Her gun 07:00 TR (00:00 ET) ve 19:00 TR (12:00 ET) zamanlanmistir.
#
# Manuel test: PowerShell'de su komutu calistir:
#   .\run_pipeline.ps1
# =============================================================================

$env:PYTHONUTF8 = "1"

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$BACKEND_DIR = Join-Path $SCRIPT_DIR "backend"
$LOG_DIR = Join-Path $BACKEND_DIR "app\logs"

# Log dizini yoksa olustur
if (-not (Test-Path $LOG_DIR)) {
    New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null
}

$LOG_FILE = Join-Path $LOG_DIR "task_scheduler.log"
$TIMESTAMP = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

Add-Content -Path $LOG_FILE -Value ""
Add-Content -Path $LOG_FILE -Value "========================================"
Add-Content -Path $LOG_FILE -Value "[$TIMESTAMP] Task Scheduler tetiklendi"
Add-Content -Path $LOG_FILE -Value "========================================"

# Calisma dizinini backend olarak ayarla
Set-Location $BACKEND_DIR

# Pipeline'i calistir
try {
    $output = uv run python run_daily_pipelines.py 2>&1
    Add-Content -Path $LOG_FILE -Value $output
    Add-Content -Path $LOG_FILE -Value "[$TIMESTAMP] Pipeline basariyla tamamlandi."
    exit 0
} catch {
    $err = $_.Exception.Message
    Add-Content -Path $LOG_FILE -Value "[$TIMESTAMP] HATA: $err"
    exit 1
}
