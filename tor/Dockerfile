# Use Alpine as the base image
FROM alpine:latest

# Create a tor user (if not done already) and setup directories
RUN adduser -D tor && \
    mkdir -p /etc/tor && \
    chown tor:tor /etc/tor

# Install Tor
RUN apk add --no-cache tor

# Copy torrc from the build directory into the container
COPY torrc /etc/tor/torrc

# Ensure the torrc file is owned by the Tor user
RUN chown tor:tor /etc/tor/torrc

# Switch to the Tor user
USER tor

# Set the entrypoint and default command
ENTRYPOINT ["tor"]
CMD ["-f", "/etc/tor/torrc"]
