#!/bin/bash

# Run the script using:
# 
# curl -fsSL "curl -fsSL "https://raw.githubusercontent.com/lenadlm/docker/main/tmp/docker.sh" -o "docker.sh"
# chmod +x docker.sh
# sudo ./docker.sh

# Exit immediately if a command exits with a non-zero status
set -e

# Define log file
LOG_FILE="/var/log/docker_setup.log"
exec > >(tee -a $LOG_FILE) 2>&1

# Variables
INTERNAL_NETWORK="internal_network"
EXTERNAL_NETWORK="external_network"
INTERNAL_SUBNET="172.30.0.0/24"
INTERNAL_GATEWAY="172.30.0.1"
EXTERNAL_SUBNET="172.20.0.0/24"
EXTERNAL_GATEWAY="172.20.0.1"
PORTAINER_DIR="/docker/portainer"
PORTAINER_COMPOSE_URL="https://raw.githubusercontent.com/lenadlm/docker/main/tmp/docker-compose.yml"

# Function to handle errors
error_exit() {
    echo "Error on line $1"
    exit 1
}
trap 'error_exit $LINENO' ERR

# Check OS compatibility
OS=$(lsb_release -si 2>/dev/null || cat /etc/*release 2>/dev/null | grep -oP '(?<=^ID=).+')
if [[ "$OS" != "Ubuntu" && "$OS" != "Debian" ]]; then
    echo "Unsupported OS: $OS. This script supports only Ubuntu and Debian."
    exit 1
fi

echo "Running on supported OS: $OS"

# Update and install dependencies
echo "Updating and installing dependencies..."
apt update && apt upgrade -y
apt install -y curl gnupg lsb-release ca-certificates software-properties-common
apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Docker if not already installed
if ! command -v docker &>/dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
else
    echo "Docker is already installed. Skipping installation."
fi

# Ensure Docker service is running
echo "Enabling and starting Docker service..."
systemctl enable --now docker

# Add user 'lenadlm' to Docker group if it exists
if id "leo" &>/dev/null; then
    echo "Adding user 'leo' to Docker group..."
    usermod -aG docker leo
else
    echo "User 'leo' does not exist. Skipping user modification."
fi

# Check and create internal network
if ! docker network inspect "$INTERNAL_NETWORK" &>/dev/null; then
    echo "Creating docker network: $INTERNAL_NETWORK"
    docker network create \
        --subnet=$INTERNAL_SUBNET \
        --gateway=$INTERNAL_GATEWAY \
        $INTERNAL_NETWORK
else
    echo "Docker network $INTERNAL_NETWORK already exists."
fi

# Check and create external network
if ! docker network inspect "$EXTERNAL_NETWORK" &>/dev/null; then
    echo "Creating docker network: $EXTERNAL_NETWORK"
    docker network create \
        --subnet=$EXTERNAL_SUBNET \
        --gateway=$EXTERNAL_GATEWAY \
        $EXTERNAL_NETWORK
else
    echo "Docker network $EXTERNAL_NETWORK already exists."
fi

# Setup Portainer using Docker Compose
if [ ! -d "$PORTAINER_DIR" ] || [ -z "$(docker ps -aq -f name=portainer)" ]; then
    echo "Setting up Portainer using Docker Compose..."
    mkdir -p "$PORTAINER_DIR"
    curl -fsSL "$PORTAINER_COMPOSE_URL" -o "$PORTAINER_DIR/docker-compose.yml"
    cd "$PORTAINER_DIR"
    docker compose up -d
    SERVER_IP=$(hostname -I | awk '{print $1}')
    echo "Portainer has been successfully installed and deployed using Docker Compose"
    echo "Access Portainer at: https://$SERVER_IP:9443"
else
    echo "Portainer is already installed and running. Skipping setup."
fi

echo "Docker setup completed successfully."
