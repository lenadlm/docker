#!/bin/bash

# Run the script using:
# chmod +x docker.sh
# sudo ./docker.sh

# Script to set up internal and external Docker networks and deploy Portainer
set -e

# Ensure the script is being run as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root."
    exit 1
fi

# Detect the operating system and adjust for Raspbian
OS=$(lsb_release -is 2>/dev/null | tr '[:upper:]' '[:lower:]' || echo "unknown")
if [[ $OS == "raspbian" ]]; then
    OS="debian"  # Treat Raspbian as Debian for compatibility
fi

if [[ ! $OS =~ ^(debian|ubuntu)$ ]]; then
    echo "This script only supports Debian, Ubuntu, or Raspbian."
    exit 1
fi

# Update and install prerequisites
echo "Updating system and installing prerequisites..."
apt update && apt upgrade -y
apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Install Docker if not installed
if ! command -v docker &>/dev/null; then
    echo "Docker not found. Installing..."

    # Add Docker GPG key
    echo "Adding Docker GPG key..."
    curl -fsSL https://download.docker.com/linux/$OS/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg || {
        echo "Failed to fetch Docker GPG key. Exiting."; exit 1; }

    # Add Docker repository
    echo "Adding Docker repository..."
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
https://download.docker.com/linux/$OS $(lsb_release -cs) stable" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Update package list and install Docker
    apt update
    apt install -y docker-ce docker-ce-cli containerd.io
    systemctl enable docker
    systemctl start docker
else
    echo "Docker is already installed. Skipping installation."
fi

# Install Docker Compose plugin if not installed
if ! docker compose version &>/dev/null; then
    echo "Docker Compose (plugin) not found. Installing..."
    apt install -y docker-compose-plugin
else
    echo "Docker Compose (plugin) is already installed. Skipping installation."
fi

# Remove existing portainer_default network if it exists
#if docker network inspect portainer_default >/dev/null 2>&1; then
#    echo "Removing old 'portainer_default' network..."
#    docker network rm portainer_default
#fi

# Create the internal Docker network
if ! docker network inspect internal_network >/dev/null 2>&1; then
    echo "Creating the internal_network Docker network..."
    docker network create \
        --driver bridge \
        --subnet=172.30.0.0/24 \
        --gateway=172.30.0.1 \
        --attachable \
        internal_network
else
    echo "Network 'internal_network' already exists. Skipping creation."
fi

# Create the external Docker network
if ! docker network inspect external_network >/dev/null 2>&1; then
    echo "Creating the external_network Docker network..."
    docker network create \
        --driver bridge \
        --subnet=172.20.0.0/24 \
        --gateway=172.20.0.1 \
        --attachable \
        external_network
else
    echo "Network 'external_network' already exists. Skipping creation."
fi

# Define variables for deployment
COMPOSE_FILE_URL="https://raw.githubusercontent.com/lenadlm/docker/main/srv-1/portainer/docker-compose.yml"
COMPOSE_DIR="/opt/docker/portainer"

# Check if the URL is accessible
echo "Validating Docker Compose file URL..."
if ! curl -Isf $COMPOSE_FILE_URL; then
    echo "The specified URL is not accessible: $COMPOSE_FILE_URL"
    exit 1
fi

# Download the docker-compose file to the target directory
echo "Downloading Docker Compose file..."
mkdir -p $COMPOSE_DIR
curl -fsSL $COMPOSE_FILE_URL -o $COMPOSE_DIR/docker-compose.yml

# Update the compose file to use the new networks
echo "Updating Docker Compose file to use internal_network..."
sed -i 's/portainer_default/internal_network/g' $COMPOSE_DIR/docker-compose.yml

# Navigate to the compose directory and deploy Portainer using Docker Compose
echo "Deploying Portainer using Docker Compose..."
cd $COMPOSE_DIR
docker compose up -d

# Print success message
SERVER_IP=$(hostname -I | awk '{print $1}')
cat <<EOF
Portainer has been successfully installed and deployed using Docker Compose (plugin version).
The Docker Compose file is located at: $COMPOSE_DIR/docker-compose.yml
Access Portainer at: https://$SERVER_IP:9443

Please configure Portainer via the web interface.
EOF
