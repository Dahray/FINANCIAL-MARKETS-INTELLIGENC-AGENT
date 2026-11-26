# ==============================================================================
# FMIP Safe Credential Configuration Utility (PowerShell)
# ==============================================================================
# Prompts for API keys with hidden input (-AsSecureString) and updates .env
# locally so secret keys are never printed to the screen or leaked into chat logs.

$ErrorActionPreference = "Stop"
$EnvPath = Join-Path $PSScriptRoot "..\.env"
$ExamplePath = Join-Path $PSScriptRoot "..\.env.example"

if (-not (Test-Path $EnvPath)) {
    Copy-Item $ExamplePath $EnvPath
    Write-Output "Created .env from .env.example"
}

function Set-EnvVariable {
    param (
        [string]$Key,
        [string]$Value
    )
    if ([string]::IsNullOrWhiteSpace($Value)) {
        return
    }
    $Content = Get-Content $EnvPath -Raw
    $Pattern = "(?m)^" + [regex]::Escape($Key) + "=.*$"
    if ($Content -match $Pattern) {
        $Content = [regex]::Replace($Content, $Pattern, "$Key=$Value")
    } else {
        $Content = $Content.TrimEnd() + "`r`n$Key=$Value`r`n"
    }
    Set-Content -Path $EnvPath -Value $Content -NoNewline
    Write-Output "  [SAVED] $Key updated in .env"
}

function Read-SecretValue {
    param ([string]$PromptText)
    $Secure = Read-Host -Prompt "$PromptText (input hidden, press Enter to skip)" -AsSecureString
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
    try {
        return [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
    } finally {
        [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)
    }
}

Write-Output "=========================================================================="
Write-Output "SOHCAHTOA FMIP - SAFE API CREDENTIAL ONBOARDING WIZARD"
Write-Output "Press Enter on any prompt to keep existing value in .env"
Write-Output "=========================================================================="

Set-EnvVariable -Key "GEMINI_API_KEY" -Value (Read-SecretValue "1. Enter GEMINI_API_KEY")
Set-EnvVariable -Key "TAVILY_API_KEY" -Value (Read-SecretValue "2. Enter TAVILY_API_KEY")
Set-EnvVariable -Key "FMP_API_KEY" -Value (Read-SecretValue "3a. Enter FMP_API_KEY (Financial Modeling Prep)")
Set-EnvVariable -Key "ALPHA_VANTAGE_API_KEY" -Value (Read-SecretValue "3b. Enter ALPHA_VANTAGE_API_KEY")
Set-EnvVariable -Key "FRED_API_KEY" -Value (Read-SecretValue "4. Enter FRED_API_KEY (St. Louis Fed)")

$SmtpUser = Read-Host -Prompt "5a. Enter Gmail Address for SMTP_USERNAME (press Enter to skip)"
if (-not [string]::IsNullOrWhiteSpace($SmtpUser)) {
    Set-EnvVariable -Key "SMTP_USERNAME" -Value $SmtpUser
    Set-EnvVariable -Key "EMAIL_FROM_ADDRESS" -Value $SmtpUser
    $SmtpPass = Read-SecretValue "5b. Enter 16-char Google App Password for SMTP_APP_PASSWORD"
    if (-not [string]::IsNullOrWhiteSpace($SmtpPass)) {
        Set-EnvVariable -Key "SMTP_APP_PASSWORD" -Value $SmtpPass
        Set-EnvVariable -Key "EMAIL_DELIVERY_ENABLED" -Value "true"
    }
}

$DriveFolder = Read-Host -Prompt "6. Enter GOOGLE_DRIVE_REPORTS_FOLDER_ID (press Enter to skip)"
if (-not [string]::IsNullOrWhiteSpace($DriveFolder)) {
    Set-EnvVariable -Key "GOOGLE_DRIVE_REPORTS_FOLDER_ID" -Value $DriveFolder
    Set-EnvVariable -Key "GOOGLE_DRIVE_ENABLED" -Value "true"
}

Write-Output "=========================================================================="
Write-Output "Credential setup complete. All values stored safely in: $EnvPath"
Write-Output "=========================================================================="
