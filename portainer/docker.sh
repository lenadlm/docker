#!/bin/bash

# Run the script using:
# chmod +x docker.sh
# sudo ./docker.sh

# Script to set up the portainer_default network and deploy Portainer using the new "docker compose"
set -e

# Ensure the script is being run as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root."
    exit 1
fi

# Check if the operating system is Debian, Ubuntu, or Raspbian
OS=$(lsb_release -is 2>/dev/null || echo "Unknown")
if [[ $OS == "Raspbian" ]]; then
    OS="debian"  # Raspbian uses Debian packages
fi

if [[ ! $OS =~ ^(Debian|Ubuntu|debian)$ ]]; then
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

# Check if Docker is installed, and install if missing
if ! command -v docker &>/dev/null; then
    echo "Docker not found. Installing..."
    curl -fsSL https://download.docker.com/linux/$OS/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/$OS $(lsb_release -cs) stable" \
        | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt update
    apt install -y docker-ce docker-ce-cli containerd.io
    systemctl enable docker
    systemctl start docker
else
    echo "Docker is already installed. Skipping installation."
fi

# Check if Docker Compose (plugin version) is installed, and install if missing
if ! docker compose version &>/dev/null; then
    echo "Docker Compose (plugin) not found. Installing..."
    apt install -y docker-compose-plugin
else
    echo "Docker Compose (plugin) is already installed. Skipping installation."
fi

# Create the portainer_default Docker network with a custom gateway
docker network create \
    --driver bridge \
    --subnet=172.30.0.0/24 \
    --gateway=172.30.0.1 \
    portainer_default || echo "Network 'portainer_default' already exists."

# Define variables for deployment
COMPOSE_FILE_URL="https://raw.githubusercontent.com/lenadlm/docker/main/portainer/docker-compose.yaml"
COMPOSE_DIR="/opt/docker/portainer"

# Check if the URL is accessible
if ! curl -Isf $COMPOSE_FILE_URL; then
    echo "The specified URL is not accessible. Please check the link."
    exit 1
fi

# Download the docker-compose file to the target directory
mkdir -p $COMPOSE_DIR
curl -fsSL $COMPOSE_FILE_URL -o $COMPOSE_DIR/docker-compose.yaml

# Navigate to the compose directory and deploy Portainer using the new "docker compose"
cd $COMPOSE_DIR
docker compose up -d

# Print success message
cat <<EOF
Portainer has been successfully installed and deployed using Docker Compose (plugin version).
The Docker Compose file is located at: $COMPOSE_DIR/docker-compose.yaml
Access Portainer at: https://<your_server_ip>:9443

Please configure Portainer via the web interface.
EOF
