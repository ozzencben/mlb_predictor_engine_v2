# WNBA komutlarini Docker backend ortaminda calistirir.
# Kullanim:
#   .\scripts\wnba.ps1 train --trials 60
#   .\scripts\wnba.ps1 pipeline
#   .\scripts\wnba.ps1 validate
#   .\scripts\wnba.ps1 predict

param(
    [Parameter(Position = 0)]
    [ValidateSet("train", "pipeline", "predict", "validate", "features", "shell")]
    [string]$Command = "shell",

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Image = "mlb_predictor_engine_v2-backend:latest"

function Invoke-WnbaDocker {
    param([string[]]$Cmd)

    docker run --rm `
        -v "${Root}/backend/app/sports/wnba/data:/app/app/sports/wnba/data" `
        --env-file "${Root}/.env" `
        $Image `
        @Cmd
}

switch ($Command) {
    "train" {
        $cmd = @("python", "-m", "app.sports.wnba.models.train_model")
        if ($Args -contains "--quick") {
            $cmd += "--quick"
        } else {
            $trials = "60"
            for ($i = 0; $i -lt $Args.Count; $i++) {
                if ($Args[$i] -eq "--trials" -and ($i + 1) -lt $Args.Count) {
                    $trials = $Args[$i + 1]
                }
            }
            $cmd += @("--trials", $trials)
        }
        Invoke-WnbaDocker $cmd
    }
    "pipeline" {
        $cmd = @("python", "-m", "app.sports.wnba.pipeline_runner")
        if ($Args -contains "--skip-yesterday") { $cmd += "--skip-yesterday" }
        Invoke-WnbaDocker $cmd
    }
    "predict" {
        Invoke-WnbaDocker @("python", "-m", "app.sports.wnba.models.predict")
    }
    "validate" {
        Invoke-WnbaDocker @("python", "-m", "app.sports.wnba.services.validate_data")
    }
    "features" {
        Invoke-WnbaDocker @("python", "-m", "app.sports.wnba.services.build_features")
    }
    "shell" {
        docker run --rm -it `
            -v "${Root}/backend/app/sports/wnba/data:/app/app/sports/wnba/data" `
            --env-file "${Root}/.env" `
            $Image `
            bash
    }
}
