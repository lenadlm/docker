# Use a specific Alpine version for stability
FROM alpine:latest

# Set working directory
WORKDIR /etc/tor

# Create a non-root tor user & install Tor in a single step
RUN adduser -D -u 1000 tor \
    && apk add --no-cache tor \
    && chown -R tor:tor /etc/tor

# Copy the tor configuration file
COPY --chown=tor:tor torrc torrc

# Switch to the tor user for security
USER tor

# Run Tor with the specified configuration
ENTRYPOINT ["tor"]
CMD ["-f", "/etc/tor/torrc"]
