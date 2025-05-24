#!/bin/bash

# Run the script using:
# 
# curl -fsSL "https://yourdomain.com/arch-docker.sh" -o "arch-docker.sh"
# chmod +x arch-docker.sh
# sudo ./arch-docker.sh

# Exit immediately if a command exits with a non-zero status
set -e

# Define log file
LOG_FILE="/var/log/docker_setup.log"
exec > >(tee -a "$LOG_FILE") 2>&1

# Variables
INTERNAL_NETWORK="internal_network"
EXTERNAL_NETWORK="external_network"
INTERNAL_SUBNET="172.30.0.0/24"
INTERNAL_GATEWAY="172.30.0.1"
EXTERNAL_SUBNET="172.20.0.0/24"
EXTERNAL_GATEWAY="172.20.0.1"
PORTAINER_DIR="/docker/portainer"
PORTAINER_COMPOSE_URL="https://raw.githubusercontent.com/lenadlm/docker/main/pve/portainer/docker-compose.yml"

# Function to handle errors
error_exit() {
    echo "Error on line $1"
    exit 1
}
trap 'error_exit $LINENO' ERR

# Check OS compatibility
if ! grep -qi "arch" /etc/os-release; then
    echo "Unsupported OS. This script supports only Arch Linux or Arch-based distributions."
    exit 1
fi

echo "Running on supported OS: Arch Linux"

# Update and install dependencies
echo "Updating and installing dependencies..."
pacman -Syu --noconfirm
pacman -S --noconfirm curl gnupg lsb-release ca-certificates base-devel

# Install Docker if not already installed
if ! command -v docker &>/dev/null; then
    echo "Installing Docker..."
    pacman -S --noconfirm docker
else
    echo "Docker is already installed. Skipping installation."
fi

# Ensure Docker service is running
echo "Enabling and starting Docker service..."
systemctl enable --now docker

# Add user 'leo' to Docker group if it exists
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

    # Ensure Docker Compose plugin is installed
    if ! docker compose version &>/dev/null; then
        echo "Installing Docker Compose plugin..."
        pacman -S --noconfirm docker-compose
    fi

    docker compose up -d
    SERVER_IP=$(hostname -I | awk '{print $1}')
    echo "Portainer has been successfully installed and deployed using Docker Compose"
    echo "Access Portainer at: https://$SERVER_IP:9443"
else
    echo "Portainer is already installed and running. Skipping setup."
fi

echo "Docker setup completed successfully."
