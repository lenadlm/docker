# Use Debian Bookworm Slim
FROM debian:bookworm-slim

# Install Tor and obfs4proxy
RUN apt update && \
    DEBIAN_FRONTEND=noninteractive apt install -y --no-install-recommends tor obfs4proxy && \
    useradd -m -u 1000 tor && \
    mkdir -p /var/lib/tor /var/log/tor && \
    chown -R tor:tor /etc/tor /var/lib/tor /var/log/tor && \
    chmod 700 /var/lib/tor /var/log/tor && \
    apt clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /etc/tor

# Copy torrc config with proper ownership
COPY --chown=tor:tor torrc /etc/tor/torrc

# Switch to non-root user
USER tor

# Start Tor
ENTRYPOINT ["tor"]
CMD ["-f", "/etc/tor/torrc"]
