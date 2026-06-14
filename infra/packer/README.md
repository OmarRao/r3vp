# R3VP Appliance OVA Build

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/

## Prerequisites

- Packer 1.10+
- VMware Workstation or Fusion (for vmware-iso builder)
- Internet access to download Ubuntu 22.04 ISO

## Build

```bash
cd infra/packer

# Install the VMware plugin
packer init .

# Build the OVA
packer build -var-file=appliance.pkrvars.hcl appliance.pkr.hcl
```

The OVA is written to `output/r3vp-appliance/`.

## Deploy to vSphere

1. In vCenter, go to Actions > Deploy OVF Template
2. Select the generated OVA file
3. On the "Customize template" step, fill in:
   - `r3vp.appliance_id` - from the R3VP portal (Appliances > Add New)
   - `r3vp.org_id` - your organization ID from the portal
   - `r3vp.veeam_url` - e.g. `https://veeam-server.domain.local:9419`
   - `r3vp.veeam_username` - e.g. `svc_r3vp@domain.local`
   - `r3vp.vcenter_host` - e.g. `vcenter.domain.local`
   - `r3vp.vcenter_username` - e.g. `svc_r3vp@vsphere.local`
   - `r3vp.isolated_vlan_id` - VLAN ID for isolated test networks (e.g. `4090`)
4. Power on the VM

The appliance will:
- Read OVF properties on first boot via configure-from-ovf.sh
- Write credentials to /opt/r3vp/.env
- Start the Docker container
- Register with the R3VP portal automatically

Veeam and vCenter passwords are stored in an encrypted vault.
On first boot, generate an age key and encrypt your secrets file:

```bash
# SSH into the appliance
ssh r3vp@<appliance-ip>

# Generate age key
age-keygen -o /opt/r3vp/vault/age.key

# Create and encrypt secrets
cat > /tmp/secrets.yaml <<EOF
veeam_password: "your-password"
vcenter_password: "your-password"
EOF

sops --encrypt --age $(grep "public key" /opt/r3vp/vault/age.key | awk '{print $NF}') \
  /tmp/secrets.yaml > /opt/r3vp/vault/secrets.enc.yaml

rm /tmp/secrets.yaml
sudo systemctl restart r3vp-appliance
```
