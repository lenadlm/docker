# Use a specific Alpine version
FROM alpine:latest

# Set working directory
WORKDIR /etc/tor

# Create a non-root tor user & install Tor with obfs4proxy
RUN adduser -D -u 1000 tor \
    && apk add --no-cache tor obfs4proxy \
    && mkdir -p /var/lib/tor /var/log/tor \
    && chown -R tor:tor /etc/tor /var/lib/tor /var/log/tor \
    && chmod 700 /var/lib/tor /var/log/tor

# Copy the tor configuration file
COPY --chown=tor:tor torrc /etc/tor/torrc

# Switch to the tor user for security
USER tor

# Start Tor
ENTRYPOINT ["tor"]
CMD ["-f", "/etc/tor/torrc"]
