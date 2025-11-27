FROM mcr.microsoft.com/devcontainers/python:3.11

# Install Trivy via script to avoid repo compatibility issues with Debian Testing (Trixie)
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get install -y wget apt-transport-https gnupg lsb-release curl \
    && curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin \
    && apt-get install -y make \
    && apt-get autoremove -y && apt-get clean -y && rm -rf /var/lib/apt/lists/*
