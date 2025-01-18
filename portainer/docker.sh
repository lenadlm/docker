#!/bin/bash

# Script to install Docker, set up the portainer_default network, and deploy Portainer
set -e

# Ensure the script is being run as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root."
    exit 1
fi

# Check if the operating system is Debian, Ubuntu, or Raspbian
OS=$(lsb_release -is 2>/dev/null || echo "Unknown")
if [[ ! $OS =~ ^(Debian|Ubuntu|Raspbian)$ ]]; then
    echo "This script only supports Debian, Ubuntu, or Raspbian."
    exit 1
fi

# Update and install prerequisites
apt update && apt upgrade -y
apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key and set up the repository
curl -fsSL https://download.docker.com/linux/$OS/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo \  \
"deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/$OS \ \
$(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine and Docker Compose
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Enable and start Docker service
systemctl enable docker
systemctl start docker

# Create the portainer_default Docker network
docker network create portainer_default || echo "Network 'portainer_default' already exists."

# Deploy Portainer using Docker
PORTAINER_DATA="/opt/portainer"
mkdir -p $PORTAINER_DATA
docker run -d \
    --name=portainer \
    --restart=always \
    -p 9443:9443 \
    -p 3000:3000 \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v $PORTAINER_DATA:/data \
    --network=portainer_default \
    portainer/portainer-ce

# Print success message
cat <<EOF
Portainer has been successfully installed and is accessible at:
http://<your_server_ip>:9000

Please configure Portainer via the web interface.
EOF
