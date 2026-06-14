# PowerShell companion to gen-mtls-certs.sh for Windows workstations.
# Requires: openssl.exe on PATH (ships with Git for Windows).
# Usage: .\scripts\gen-mtls-certs.ps1 -OrgId <org-id> -ApplianceName <name> [-OutDir <path>]
param(
    [Parameter(Mandatory)][string]$OrgId,
    [Parameter(Mandatory)][string]$ApplianceName,
    [string]$OutDir = ".\certs\$OrgId\$ApplianceName"
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force $OutDir | Out-Null

$caKey    = "$OutDir\r3vp-ca.key"
$caCert   = "$OutDir\r3vp-ca.crt"
$clientKey  = "$OutDir\appliance.key"
$clientCsr  = "$OutDir\appliance.csr"
$clientCert = "$OutDir\appliance.crt"
$thumbFile  = "$OutDir\thumbprint.txt"

Write-Host "-> Generating CA key and self-signed certificate..."
openssl genrsa -out $caKey 4096
openssl req -new -x509 -days 3650 -key $caKey -out $caCert `
    -subj "/O=R3VP/CN=R3VP Internal CA/OU=$OrgId"

Write-Host "-> Generating appliance client key and CSR..."
openssl genrsa -out $clientKey 2048
openssl req -new -key $clientKey -out $clientCsr `
    -subj "/O=R3VP/CN=$ApplianceName/OU=$OrgId"

Write-Host "-> Signing appliance cert with CA..."
$extFile = [System.IO.Path]::GetTempFileName()
"extendedKeyUsage=clientAuth`nsubjectAltName=DNS:$ApplianceName" | Set-Content $extFile
openssl x509 -req -days 365 `
    -in $clientCsr -CA $caCert -CAkey $caKey `
    -CAcreateserial -out $clientCert `
    -extfile $extFile
Remove-Item $extFile, $clientCsr, $caKey -ErrorAction SilentlyContinue

Write-Host "-> Computing thumbprint..."
$fp = openssl x509 -in $clientCert -noout -fingerprint -sha256
$fp -replace ".*=", "" -replace ":", "" | Set-Content $thumbFile

Write-Host ""
Write-Host "Certificates written to $OutDir\"
Write-Host "  Ship to appliance : r3vp-ca.crt, appliance.crt, appliance.key"
Write-Host "  Register in SaaS  : $(Get-Content $thumbFile)"
Write-Host ""
Write-Host "WARNING: appliance.key must never leave the customer environment."
