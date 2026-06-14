#!/usr/bin/env bash
# Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
# https://www.linkedin.com/in/omarrao/
set -euo pipefail

INSTALL_DIR="/opt/r3vp"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

info()  { echo "[INFO]  $*"; }
error() { echo "[ERROR] $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Step 1 - verify Docker is installed
# ---------------------------------------------------------------------------

info "Checking Docker installation..."
if ! command -v docker &>/dev/null; then
    error "Docker is not installed. Install Docker Engine and re-run this script."
fi

if ! docker version &>/dev/null; then
    error "Docker is installed but not reachable. Ensure the Docker daemon is running and your user has permission."
fi

info "Docker found: $(docker version --format '{{.Server.Version}}')"

# ---------------------------------------------------------------------------
# Step 2 - create directory structure
# ---------------------------------------------------------------------------

info "Creating directory structure under ${INSTALL_DIR}..."
mkdir -p "${INSTALL_DIR}/certs"
mkdir -p "${INSTALL_DIR}/vault"
info "Directories created."

# ---------------------------------------------------------------------------
# Step 3 - copy docker-compose file
# ---------------------------------------------------------------------------

COMPOSE_SRC="${REPO_ROOT}/apps/appliance/docker-compose.yml"
if [[ ! -f "${COMPOSE_SRC}" ]]; then
    error "docker-compose.yml not found at ${COMPOSE_SRC}. Run this script from inside the r3vp repository."
fi

info "Copying docker-compose.yml to ${INSTALL_DIR}..."
cp "${COMPOSE_SRC}" "${INSTALL_DIR}/docker-compose.yml"

# ---------------------------------------------------------------------------
# Step 4 - generate mTLS certificates
# ---------------------------------------------------------------------------

CERT_SCRIPT="${SCRIPT_DIR}/gen-mtls-certs.sh"
if [[ ! -f "${CERT_SCRIPT}" ]]; then
    error "Certificate generation script not found at ${CERT_SCRIPT}."
fi

info "Generating mTLS certificates into ${INSTALL_DIR}/certs/..."
bash "${CERT_SCRIPT}" --out-dir "${INSTALL_DIR}/certs"
info "Certificates generated."

# ---------------------------------------------------------------------------
# Step 5 - copy secrets template
# ---------------------------------------------------------------------------

SECRETS_SRC="${REPO_ROOT}/apps/appliance/src/vault/secrets.template.yaml"
if [[ ! -f "${SECRETS_SRC}" ]]; then
    error "Secrets template not found at ${SECRETS_SRC}."
fi

info "Copying secrets template to ${INSTALL_DIR}/vault/secrets.yaml..."
cp "${SECRETS_SRC}" "${INSTALL_DIR}/vault/secrets.yaml"

# ---------------------------------------------------------------------------
# Step 6 - print next steps
# ---------------------------------------------------------------------------

cat <<EOF

----------------------------------------------------------------------
Installation complete. Follow these steps before starting the appliance:

1. Edit the secrets file and fill in your credentials:
      ${INSTALL_DIR}/vault/secrets.yaml

2. Encrypt the secrets file with SOPS:
      sops --encrypt --in-place ${INSTALL_DIR}/vault/secrets.yaml

3. Set the required environment variables before running docker compose:
      export VEEAM_BASE_URL=https://<your-vbr-host>:9419
      export SOPS_AGE_KEY_FILE=/path/to/age-key.txt

4. Start the appliance:
      cd ${INSTALL_DIR}
      docker compose up -d

----------------------------------------------------------------------
EOF
