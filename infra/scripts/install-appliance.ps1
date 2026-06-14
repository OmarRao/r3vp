# Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
# https://www.linkedin.com/in/omarrao/
#Requires -Version 5.1
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$InstallDir   = 'C:\r3vp'
$ScriptDir    = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot     = Split-Path -Parent (Split-Path -Parent $ScriptDir)

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

function Write-Info  { param([string]$Msg) Write-Host "[INFO]  $Msg" }
function Write-Err   { param([string]$Msg) Write-Error "[ERROR] $Msg" }

# ---------------------------------------------------------------------------
# Step 1 - verify Docker is installed
# ---------------------------------------------------------------------------

Write-Info "Checking Docker installation..."

try {
    $null = docker version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Docker is installed but returned a non-zero exit code. Ensure the Docker daemon is running and your user has permission."
    }
} catch {
    Write-Err "Docker is not installed or not on PATH. Install Docker Desktop (or Docker Engine) and re-run this script."
}

Write-Info "Docker is available."

# ---------------------------------------------------------------------------
# Step 2 - create directory structure
# ---------------------------------------------------------------------------

Write-Info "Creating directory structure under $InstallDir..."
New-Item -ItemType Directory -Force -Path "$InstallDir\certs" | Out-Null
New-Item -ItemType Directory -Force -Path "$InstallDir\vault" | Out-Null
Write-Info "Directories created."

# ---------------------------------------------------------------------------
# Step 3 - copy docker-compose file
# ---------------------------------------------------------------------------

$ComposeSrc = Join-Path $RepoRoot 'apps\appliance\docker-compose.yml'
if (-not (Test-Path $ComposeSrc)) {
    Write-Err "docker-compose.yml not found at $ComposeSrc. Run this script from inside the r3vp repository."
}

Write-Info "Copying docker-compose.yml to $InstallDir..."
Copy-Item -Path $ComposeSrc -Destination "$InstallDir\docker-compose.yml" -Force
Write-Info "docker-compose.yml copied."

# ---------------------------------------------------------------------------
# Step 4 - generate mTLS certificates
# ---------------------------------------------------------------------------

$CertScript = Join-Path $ScriptDir 'gen-mtls-certs.ps1'
if (-not (Test-Path $CertScript)) {
    Write-Err "Certificate generation script not found at $CertScript."
}

Write-Info "Generating mTLS certificates into $InstallDir\certs\..."
& $CertScript -OutDir "$InstallDir\certs"
if ($LASTEXITCODE -ne 0) {
    Write-Err "Certificate generation failed. Check the output above."
}
Write-Info "Certificates generated."

# ---------------------------------------------------------------------------
# Step 5 - copy secrets template
# ---------------------------------------------------------------------------

$SecretsSrc = Join-Path $RepoRoot 'apps\appliance\src\vault\secrets.template.yaml'
if (-not (Test-Path $SecretsSrc)) {
    Write-Err "Secrets template not found at $SecretsSrc."
}

Write-Info "Copying secrets template to $InstallDir\vault\secrets.yaml..."
Copy-Item -Path $SecretsSrc -Destination "$InstallDir\vault\secrets.yaml" -Force
Write-Info "Secrets template copied."

# ---------------------------------------------------------------------------
# Step 6 - print next steps
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "----------------------------------------------------------------------"
Write-Host "Installation complete. Follow these steps before starting the appliance:"
Write-Host ""
Write-Host "1. Edit the secrets file and fill in your credentials:"
Write-Host "      $InstallDir\vault\secrets.yaml"
Write-Host ""
Write-Host "2. Encrypt the secrets file with SOPS:"
Write-Host "      sops --encrypt --in-place $InstallDir\vault\secrets.yaml"
Write-Host ""
Write-Host "3. Set the required environment variables before running docker compose:"
Write-Host "      `$env:VEEAM_BASE_URL  = 'https://<your-vbr-host>:9419'"
Write-Host "      `$env:SOPS_AGE_KEY_FILE = 'C:\path\to\age-key.txt'"
Write-Host ""
Write-Host "4. Start the appliance:"
Write-Host "      Set-Location $InstallDir"
Write-Host "      docker compose up -d"
Write-Host "----------------------------------------------------------------------"
