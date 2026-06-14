# Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
# https://www.linkedin.com/in/omarrao/
#
# Builds an Ubuntu 22.04 OVA with Docker and the R3VP appliance pre-installed.
# Deploy this OVA to vSphere, fill in OVF properties, and power on.

packer {
  required_version = ">= 1.10.0"
  required_plugins {
    vmware = {
      version = ">= 1.0.11"
      source  = "github.com/hashicorp/vmware"
    }
  }
}

variable "appliance_version" {
  type    = string
  default = "0.2.0"
}

variable "iso_url" {
  type    = string
  default = "https://releases.ubuntu.com/22.04/ubuntu-22.04.4-live-server-amd64.iso"
}

variable "iso_checksum" {
  type    = string
  default = "sha256:45f873de9f8cb637345d6e66a583762730bbea30277ef7b32c9c3bd6700a32b2"
}

variable "output_directory" {
  type    = string
  default = "output/r3vp-appliance"
}

source "vmware-iso" "appliance" {
  vm_name          = "r3vp-appliance-${var.appliance_version}"
  guest_os_type    = "ubuntu-64"
  iso_url          = var.iso_url
  iso_checksum     = var.iso_checksum
  disk_size        = 20480
  memory           = 2048
  cpus             = 2
  headless         = true
  http_directory   = "http"
  boot_command = [
    "<esc><wait>",
    "linux /casper/vmlinuz quiet autoinstall ds=nocloud-net;s=http://{{ .HTTPIP }}:{{ .HTTPPort }}/ <enter>",
    "initrd /casper/initrd <enter>",
    "boot <enter>",
  ]
  boot_wait            = "5s"
  shutdown_command     = "echo 'packer' | sudo -S shutdown -P now"
  ssh_username         = "r3vp"
  ssh_password         = "r3vp"
  ssh_timeout          = "30m"
  output_directory     = var.output_directory
  skip_export          = false
  format               = "ova"
  ovf_template         = "ovf-template.xml"
}

build {
  sources = ["source.vmware-iso.appliance"]

  # Install Docker
  provisioner "shell" {
    inline = [
      "sudo apt-get update -qq",
      "sudo apt-get install -y ca-certificates curl gnupg",
      "sudo install -m 0755 -d /etc/apt/keyrings",
      "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg",
      "sudo chmod a+r /etc/apt/keyrings/docker.gpg",
      "echo \"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable\" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null",
      "sudo apt-get update -qq",
      "sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin",
      "sudo usermod -aG docker r3vp",
      "sudo systemctl enable docker",
    ]
  }

  # Install open-vm-tools for vSphere OVF property support
  provisioner "shell" {
    inline = [
      "sudo apt-get install -y open-vm-tools cloud-init",
    ]
  }

  # Install sops and age for secret decryption
  provisioner "shell" {
    inline = [
      "curl -sSL https://github.com/getsops/sops/releases/download/v3.8.1/sops-v3.8.1.linux.amd64 -o /tmp/sops",
      "sudo install /tmp/sops /usr/local/bin/sops",
      "curl -sSL https://github.com/FiloSottile/age/releases/download/v1.1.1/age-v1.1.1-linux-amd64.tar.gz | sudo tar -xz -C /usr/local/bin --strip-components=1 age/age age/age-keygen",
    ]
  }

  # Copy appliance files and systemd service
  provisioner "file" {
    source      = "../../apps/appliance/"
    destination = "/opt/r3vp/"
  }

  provisioner "file" {
    source      = "systemd/r3vp-appliance.service"
    destination = "/tmp/r3vp-appliance.service"
  }

  provisioner "shell" {
    inline = [
      "sudo mv /tmp/r3vp-appliance.service /etc/systemd/system/r3vp-appliance.service",
      "sudo systemctl enable r3vp-appliance",
      "sudo mkdir -p /opt/r3vp/certs /opt/r3vp/vault",
    ]
  }
}
