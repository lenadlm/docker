#!/bin/bash

# Run the script using:
# 
# curl -fsSL "https://raw.githubusercontent.com/lenadlm/docker/main/tmp/docker.sh" -o "docker.sh"
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
PORTAINER_COMPOSE_URL="https://raw.githubusercontent.com/lenadlm/docker/main/tmp/portainer/docker-compose.yml"

# Function to handle errors
error_exit() {
    echo "Error on line $1"
    exit 1
}
trap 'error_exit $LINENO' ERR

# Check OS compatibility - Improved detection
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_CODENAME
elif [ -f /etc/debian_version ]; then
    OS="debian"
    VERSION=$(cat /etc/debian_version)
elif [ -f /etc/lsb-release ]; then
    . /etc/lsb-release
    OS=$DISTRIB_ID
    VERSION=$DISTRIB_CODENAME
else
    echo "Cannot determine OS. This script supports only Ubuntu and Debian."
    exit 1
fi

# Convert to lowercase for comparison
OS=$(echo "$OS" | tr '[:upper:]' '[:lower:]')

if [[ "$OS" != "ubuntu" && "$OS" != "debian" ]]; then
    echo "Unsupported OS: $OS. This script supports only Ubuntu and Debian."
    exit 1
fi

echo "Running on supported OS: $OS $VERSION"

# Update and install dependencies - Conditional package installation
echo "Updating and installing dependencies..."
apt update && apt upgrade -y

# Install common packages
COMMON_PACKAGES="curl gnupg lsb-release ca-certificates"

# Add Ubuntu-specific packages
if [[ "$OS" == "ubuntu" ]]; then
    echo "Ubuntu detected: Installing Ubuntu-specific packages..."
    apt install -y $COMMON_PACKAGES software-properties-common
else
    echo "Debian detected: Installing Debian-specific packages..."
    # On Debian, we need different packages for repository management
    apt install -y $COMMON_PACKAGES apt-transport-https
fi

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

# Wait a moment for Docker to be fully ready
sleep 3

# Add user 'leo' to Docker group if it exists
if id "leo" &>/dev/null; then
    echo "Adding user 'leo' to Docker group..."
    usermod -aG docker leo
    echo "User 'leo' added to docker group. You may need to log out and back in for changes to take effect."
else
    echo "User 'leo' does not exist. Skipping user modification."
fi

# Install Docker Compose plugin if not present
if ! docker compose version &>/dev/null; then
    echo "Installing Docker Compose plugin..."
    apt update
    apt install -y docker-compose-plugin
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
# Check if portainer directory exists and if portainer container is running
if [ ! -d "$PORTAINER_DIR" ] || ! docker ps --format '{{.Names}}' | grep -q "^portainer$"; then
    echo "Setting up Portainer using Docker Compose..."
    mkdir -p "$PORTAINER_DIR"
    
    # Download docker-compose.yml if it doesn't exist
    if [ ! -f "$PORTAINER_DIR/docker-compose.yml" ]; then
        curl -fsSL "$PORTAINER_COMPOSE_URL" -o "$PORTAINER_DIR/docker-compose.yml"
    fi
    
    cd "$PORTAINER_DIR"
    docker compose up -d
    
    # Get server IP
    SERVER_IP=$(hostname -I | awk '{print $1}')
    if [ -z "$SERVER_IP" ]; then
        SERVER_IP="localhost"
    fi
    
    echo "Portainer has been successfully installed and deployed using Docker Compose"
    echo "Access Portainer at: https://$SERVER_IP:9443"
    echo "First-time setup: Create an admin user when you first access Portainer"
else
    echo "Portainer is already installed and running. Skipping setup."
fi

echo "Docker setup completed successfully on $OS $VERSION"
echo "Log file saved at: $LOG_FILE"
