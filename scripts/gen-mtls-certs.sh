#!/usr/bin/env bash
# Generate mTLS certificate pair for a new appliance registration.
# Usage: ./scripts/gen-mtls-certs.sh <org-id> <appliance-name> [output-dir]
#
# Requires: openssl
# Produces:
#   <output-dir>/r3vp-ca.crt      — R3VP CA certificate (ship to appliance)
#   <output-dir>/appliance.crt    — Appliance client cert (ship to appliance)
#   <output-dir>/appliance.key    — Appliance private key  (NEVER leaves appliance)
#   <output-dir>/thumbprint.txt   — SHA-256 thumbprint to register in SaaS DB

set -euo pipefail

ORG_ID="${1:?Usage: $0 <org-id> <appliance-name> [output-dir]}"
APPLIANCE_NAME="${2:?Usage: $0 <org-id> <appliance-name> [output-dir]}"
OUT_DIR="${3:-./certs/${ORG_ID}/${APPLIANCE_NAME}}"

mkdir -p "${OUT_DIR}"

CA_KEY="${OUT_DIR}/r3vp-ca.key"
CA_CERT="${OUT_DIR}/r3vp-ca.crt"
CLIENT_KEY="${OUT_DIR}/appliance.key"
CLIENT_CSR="${OUT_DIR}/appliance.csr"
CLIENT_CERT="${OUT_DIR}/appliance.crt"

echo "→ Generating CA key and self-signed certificate…"
openssl genrsa -out "${CA_KEY}" 4096
openssl req -new -x509 -days 3650 -key "${CA_KEY}" -out "${CA_CERT}" \
  -subj "/O=R3VP/CN=R3VP Internal CA/OU=${ORG_ID}"

echo "→ Generating appliance client key and CSR…"
openssl genrsa -out "${CLIENT_KEY}" 2048
openssl req -new -key "${CLIENT_KEY}" -out "${CLIENT_CSR}" \
  -subj "/O=R3VP/CN=${APPLIANCE_NAME}/OU=${ORG_ID}"

echo "→ Signing appliance cert with CA…"
openssl x509 -req -days 365 \
  -in "${CLIENT_CSR}" -CA "${CA_CERT}" -CAkey "${CA_KEY}" \
  -CAcreateserial -out "${CLIENT_CERT}" \
  -extfile <(printf "extendedKeyUsage=clientAuth\nsubjectAltName=DNS:%s" "${APPLIANCE_NAME}")

echo "→ Computing thumbprint…"
openssl x509 -in "${CLIENT_CERT}" -noout -fingerprint -sha256 \
  | sed 's/://g' | awk -F= '{print $2}' > "${OUT_DIR}/thumbprint.txt"

rm -f "${CLIENT_CSR}" "${CA_KEY}"  # CA key no longer needed locally

echo ""
echo "✓ Certificates written to ${OUT_DIR}/"
echo "  Ship to appliance: r3vp-ca.crt, appliance.crt, appliance.key"
echo "  Register thumbprint in SaaS: $(cat "${OUT_DIR}/thumbprint.txt")"
echo ""
echo "⚠ Keep appliance.key confidential — it never leaves the customer environment."
