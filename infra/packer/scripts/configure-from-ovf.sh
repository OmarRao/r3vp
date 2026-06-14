#!/usr/bin/env bash
# Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
# https://www.linkedin.com/in/omarrao/
#
# Reads OVF properties injected by vSphere and writes /opt/r3vp/.env
# Runs before the Docker container starts on each boot.

set -euo pipefail

ENV_FILE="/opt/r3vp/.env"
OVF_ENV="/run/vmware/ovfenv"

# If no OVF environment is present, skip (manual .env configuration)
if [ ! -f "$OVF_ENV" ] && ! command -v vmtoolsd &>/dev/null; then
  echo "No OVF environment found, skipping auto-configuration"
  exit 0
fi

# Try to read OVF properties via vmtoolsd
if command -v vmtoolsd &>/dev/null; then
  get_ovf() {
    vmtoolsd --cmd "info-get guestinfo.ovfenv" 2>/dev/null | \
      grep -oP "(?<=key=\"${1}\" value=\")[^\"]*" || echo ""
  }

  APPLIANCE_ID=$(get_ovf "r3vp.appliance_id")
  ORG_ID=$(get_ovf "r3vp.org_id")
  SAAS_BASE_URL=$(get_ovf "r3vp.saas_base_url")
  VEEAM_URL=$(get_ovf "r3vp.veeam_url")
  VEEAM_USERNAME=$(get_ovf "r3vp.veeam_username")
  VCENTER_HOST=$(get_ovf "r3vp.vcenter_host")
  VCENTER_USERNAME=$(get_ovf "r3vp.vcenter_username")
  ISOLATED_VLAN_ID=$(get_ovf "r3vp.isolated_vlan_id")

  if [ -n "$APPLIANCE_ID" ]; then
    cat > "$ENV_FILE" <<EOF
R3VP_APPLIANCE_ID=${APPLIANCE_ID}
R3VP_ORG_ID=${ORG_ID}
R3VP_SAAS_BASE_URL=${SAAS_BASE_URL:-https://api.r3vp.io}
R3VP_MTLS_CERT_PATH=/certs/client.crt
R3VP_MTLS_KEY_PATH=/certs/client.key
R3VP_MTLS_CA_PATH=/certs/ca.crt
R3VP_VEEAM_URL=${VEEAM_URL}
R3VP_VEEAM_USERNAME=${VEEAM_USERNAME}
R3VP_VCENTER_HOST=${VCENTER_HOST}
R3VP_VCENTER_USERNAME=${VCENTER_USERNAME}
R3VP_ISOLATED_VLAN_ID=${ISOLATED_VLAN_ID:-4090}
R3VP_VAULT_PATH=/vault/secrets.enc.yaml
R3VP_AGE_KEY_PATH=/vault/age.key
EOF
    echo "OVF configuration written to ${ENV_FILE}"
  else
    echo "OVF appliance_id not set, skipping auto-configuration"
  fi
fi
