# docker/Dockerfile — single image with all tooling
FROM node:22-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    git jq curl ca-certificates unzip \
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
    npm install -g --ignore-scripts @earendil-works/pi-coding-agent && \
    npm install -g @jetbrains/junie && \
    npm install -g cline && \
    npm install -g @kilocode/cli

# Install Kimi Code CLI (curl installer — not on npm)
RUN curl -fsSL https://code.kimi.com/kimi-code/install.sh | bash

# Install Bun then AutoHand Code CLI (requires Bun runtime)
RUN curl -fsSL https://bun.sh/install | bash && \
    export PATH="/root/.bun/bin:$PATH" && \
    curl -fsSL https://autohand.ai/install.sh | bash
ENV PATH="/root/.kimi-code/bin:/root/.bun/bin:${PATH}"

# Install Grok Build (curl installer, not npm)
# SHA256 pins the installer script for reproducibility — update both when upgrading grok
RUN curl -fsSL -o /tmp/grok-install.sh https://x.ai/cli/install.sh && \
    echo "5b74aa23e096d798a28a526c57daf5506eb2597de73ab7c37f742db20fcdbfb7  /tmp/grok-install.sh" | sha256sum -c - && \
    bash /tmp/grok-install.sh && \
    rm /tmp/grok-install.sh && \
    grok --version

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
