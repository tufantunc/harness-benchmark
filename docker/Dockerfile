# docker/Dockerfile — single image with all tooling
FROM node:22-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    git jq curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python testing tools
RUN python3 -m pip install --break-system-packages pytest

# JavaScript testing dependencies (shared node_modules for jest + babel)
RUN mkdir -p /npm-install
WORKDIR /npm-install
RUN npm init -y && \
    npm install jest@29.7.0 @babel/core @exercism/babel-preset-javascript && \
    echo '{"presets":["@exercism/babel-preset-javascript"]}' > babel.config.js

# Install harness CLIs globally
RUN npm install -g opencode-ai && \
    npm install -g --ignore-scripts @earendil-works/pi-coding-agent

# Copy container helpers
COPY container/ /app/container/
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh /app/container/*.sh

# Copy polyglot-benchmark data (baked in, read-only)
COPY polyglot-benchmark/ /app/polyglot-benchmark/

# Copy harness adapters
COPY harnesses/ /app/harnesses/

WORKDIR /app

ENTRYPOINT ["/app/entrypoint.sh"]
