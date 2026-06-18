# =============================================================================
# Legends Sports -- Windows Task Scheduler Kurulum Scripti
# =============================================================================
# Kullanim:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
#   .\setup_scheduler.ps1
#
# Kurulacak gorevler:
#   LegendsSports_Pipeline_Midnight  -> Her gun 07:00 TR (00:00 ET)
#   LegendsSports_Pipeline_Noon      -> Her gun 19:00 TR (12:00 ET)
# =============================================================================

$SCRIPT_DIR  = Split-Path -Parent $MyInvocation.MyCommand.Path
$PS1_SCRIPT  = Join-Path $SCRIPT_DIR "run_pipeline.ps1"
$PS_EXE      = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
$TASK_ARGS   = "-NonInteractive -NoProfile -ExecutionPolicy Bypass -File `"$PS1_SCRIPT`""

Write-Host "============================================="
Write-Host " Legends Sports Task Scheduler Kurulumu"
Write-Host "============================================="
Write-Host "Script: $PS1_SCRIPT"
Write-Host ""

# Gorev 1: 07:00 TR her gun (00:00 ET)
$t1 = "LegendsSports_Pipeline_Midnight"
schtasks /delete /tn $t1 /f 2>$null | Out-Null
$r1 = schtasks /create /tn $t1 `
    /tr "`"$PS_EXE`" $TASK_ARGS" `
    /sc DAILY /st 07:00 `
    /f /rl HIGHEST 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "OK: $t1 --> 07:00 TR her gun"
} else {
    # HIGHEST (admin) basarisiz, normal seviye ile tekrar dene
    schtasks /delete /tn $t1 /f 2>$null | Out-Null
    $r1 = schtasks /create /tn $t1 `
        /tr "`"$PS_EXE`" $TASK_ARGS" `
        /sc DAILY /st 07:00 /f 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK: $t1 --> 07:00 TR her gun (normal kullanici seviyesi)"
    } else {
        Write-Host "HATA: $t1 kaydedilemedi: $r1"
    }
}

# Gorev 2: 19:00 TR her gun (12:00 ET)
$t2 = "LegendsSports_Pipeline_Noon"
schtasks /delete /tn $t2 /f 2>$null | Out-Null
$r2 = schtasks /create /tn $t2 `
    /tr "`"$PS_EXE`" $TASK_ARGS" `
    /sc DAILY /st 19:00 `
    /f /rl HIGHEST 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "OK: $t2 --> 19:00 TR her gun"
} else {
    schtasks /delete /tn $t2 /f 2>$null | Out-Null
    $r2 = schtasks /create /tn $t2 `
        /tr "`"$PS_EXE`" $TASK_ARGS" `
        /sc DAILY /st 19:00 /f 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK: $t2 --> 19:00 TR her gun (normal kullanici seviyesi)"
    } else {
        Write-Host "HATA: $t2 kaydedilemedi: $r2"
    }
}

Write-Host ""
Write-Host "============================================="
Write-Host " KURULUM TAMAMLANDI"
Write-Host " Calistirma zamanlari:"
Write-Host "   07:00 TR = 00:00 ET (gece yarisi)"
Write-Host "   19:00 TR = 12:00 ET (oglen)"
Write-Host ""
Write-Host " Gorevi dogrula:"
Write-Host "   schtasks /query /tn LegendsSports_Pipeline_Midnight"
Write-Host "   schtasks /query /tn LegendsSports_Pipeline_Noon"
Write-Host ""
Write-Host " Log dosyasi:"
Write-Host "   backend\app\logs\task_scheduler.log"
Write-Host "============================================="
