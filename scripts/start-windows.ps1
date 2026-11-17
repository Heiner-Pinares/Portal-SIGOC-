param([string]$Bind = "0.0.0.0:8000")
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Get-DotEnvValue([string]$Name) {
    $envFile = Join-Path $ProjectRoot ".env"
    if (-not (Test-Path -LiteralPath $envFile)) { return $null }
    $pattern = "^\s*" + [Regex]::Escape($Name) + "\s*=(.*)$"
    $matchLine = Get-Content -LiteralPath $envFile |
        Where-Object { $_ -match $pattern } |
        Select-Object -Last 1
    if ($null -eq $matchLine) { return $null }
    $value = ([Regex]::Match($matchLine, $pattern).Groups[1].Value).Trim()
    return $value.Trim('"').Trim("'")
}

function Import-SecretFile(
    [string]$FileVariable,
    [string]$TargetVariable,
    [bool]$Required
) {
    $configuredPath = [Environment]::GetEnvironmentVariable($FileVariable, "Process")
    if ([string]::IsNullOrWhiteSpace($configuredPath)) {
        $configuredPath = Get-DotEnvValue $FileVariable
    }

    if (-not [string]::IsNullOrWhiteSpace($configuredPath)) {
        if (-not [IO.Path]::IsPathRooted($configuredPath)) {
            $configuredPath = Join-Path $ProjectRoot $configuredPath
        }
        if (-not (Test-Path -LiteralPath $configuredPath -PathType Leaf)) {
            throw "No existe el archivo configurado en $FileVariable."
        }
        $secretValue = (Get-Content -Raw -LiteralPath $configuredPath).TrimEnd("`r", "`n")
        if ([string]::IsNullOrEmpty($secretValue)) {
            throw "El archivo configurado en $FileVariable esta vacio."
        }
        [Environment]::SetEnvironmentVariable($TargetVariable, $secretValue, "Process")
        Write-Host "$TargetVariable cargado desde archivo protegido."
        return
    }

    $currentValue = [Environment]::GetEnvironmentVariable($TargetVariable, "Process")
    if ($Required -and [string]::IsNullOrWhiteSpace($currentValue)) {
        throw "Configure $FileVariable en .env antes de iniciar SIGOC."
    }
}

# Carga los secretos solo en la memoria del proceso; nunca imprime sus valores.
Import-SecretFile "APP_SECRET_KEY_FILE" "APP_SECRET_KEY" $true
Import-SecretFile "PVUDB_PASSWORD_FILE" "PVUDB_PASSWORD" $false
Import-SecretFile "DWO_PASSWORD_FILE" "DWO_PASSWORD" $false

$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "No existe .venv. Ejecute la instalacion primero."
}
& $python -m waitress --listen=$Bind wsgi:app

