# ClawBots OpenSim Server
# Runs OpenSim standalone with Bhairav Temple region

FROM mcr.microsoft.com/dotnet/runtime:8.0

LABEL maintainer="Kalrav <kalrav-dev@proton.me>"
LABEL description="ClawBots OpenSim Server - AI Agent Virtual World"

# Install dependencies
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    libgdiplus \
    && rm -rf /var/lib/apt/lists/*

# Create opensim user
RUN useradd -m -s /bin/bash opensim

# Download and extract OpenSim
WORKDIR /opt
RUN wget -q http://opensimulator.org/dist/opensim-0.9.3.0.tar.gz \
    && tar xzf opensim-0.9.3.0.tar.gz \
    && rm opensim-0.9.3.0.tar.gz \
    && mv opensim-0.9.3.0 opensim \
    && chown -R opensim:opensim /opt/opensim

# Copy configuration
COPY config/ /opt/opensim/bin/

# Set permissions
RUN chown -R opensim:opensim /opt/opensim

# Switch to opensim user
USER opensim
WORKDIR /opt/opensim/bin

# Expose ports
# 9000 - Region port (TCP/UDP)
# 9001 - RemoteAdmin (TCP)
EXPOSE 9000/tcp 9000/udp 9001/tcp

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
    CMD curl -sf http://localhost:9000/get_grid_info || exit 1

# Start OpenSim
CMD ["dotnet", "OpenSim.dll"]
