[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z][a-z0-9-]{4,28}[a-z0-9]$')]
    [string]$ProjectId,
    [string]$Region = 'asia-southeast1',
    [ValidatePattern('^[a-z][a-z0-9-]*[a-z0-9]$')]
    [string]$Service = 'weather-mcp',
    [string]$SecretName = 'weatherapi-key',
    [ValidatePattern('^[0-9]+$')]
    [string]$SecretVersion = '1',
    [string]$ServiceAccount,
    [switch]$AllowUnauthenticated,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
if (-not $ServiceAccount) {
    $ServiceAccount = "$Service-runner@$ProjectId.iam.gserviceaccount.com"
}

$deployArguments = @(
    'run', 'deploy', $Service,
    '--project', $ProjectId,
    '--region', $Region,
    '--source', $PSScriptRoot,
    '--service-account', $ServiceAccount,
    '--set-secrets', "WEATHERAPI_KEY=${SecretName}:${SecretVersion}",
    '--port', '8080', '--memory', '512Mi', '--cpu', '1',
    '--concurrency', '20', '--timeout', '300',
    '--min-instances', '0', '--max-instances', '2'
)
if ($AllowUnauthenticated) {
    $deployArguments += '--allow-unauthenticated'
} else {
    $deployArguments += '--no-allow-unauthenticated'
}

if ($DryRun) {
    Write-Output 'Dry run: no Google Cloud resources or IAM permissions will be changed.'
    Write-Output ('gcloud ' + ($deployArguments -join ' '))
    return
}

if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    throw 'Install Google Cloud CLI and run gcloud auth login first. See CLOUD_RUN.md.'
}

function Invoke-CheckedGcloud {
    param([string[]]$Arguments)
    & gcloud @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "gcloud failed with exit code $LASTEXITCODE. Deployment stopped."
    }
}

# Validate metadata only. Never fetch or print a secret payload.
Invoke-CheckedGcloud -Arguments @('secrets', 'versions', 'describe', $SecretVersion,
    '--secret', $SecretName, '--project', $ProjectId, '--format=value(state)')
Invoke-CheckedGcloud -Arguments @('iam', 'service-accounts', 'describe', $ServiceAccount,
    '--project', $ProjectId, '--format=value(email)')
Invoke-CheckedGcloud -Arguments $deployArguments
$serviceUrl = Invoke-CheckedGcloud -Arguments @('run', 'services', 'describe', $Service,
    '--project', $ProjectId, '--region', $Region, '--format=value(status.url)')
Write-Output "MCP_SERVER_URL=$($serviceUrl.TrimEnd('/'))/mcp"
Write-Output 'Update the repository root .env, restart ADK Web, then run verify_setup.py.'
