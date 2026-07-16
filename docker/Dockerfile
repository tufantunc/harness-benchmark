# docker/Dockerfile — single image with all tooling
FROM node:22-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    git jq curl ca-certificates unzip \
    && rm -rf /var/lib/apt/lists/*

# Python testing tools + YAML parser for entrypoint manifest reading
RUN python3 -m pip install --break-system-packages pytest pyyaml

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

# Install Kimi Code CLI (curl installer — SHA256 pinned)
RUN curl -fsSL -o /tmp/kimi-install.sh https://code.kimi.com/kimi-code/install.sh && \
    echo "638927825e96825edbb563de5e0cb06f8a0551c53e026ade8b717b0f25cb83d2  /tmp/kimi-install.sh" | sha256sum -c - && \
    bash /tmp/kimi-install.sh && \
    rm /tmp/kimi-install.sh

# Install Bun (SHA256 pinned) then AutoHand Code CLI (SHA256 pinned)
RUN curl -fsSL -o /tmp/bun-install.sh https://bun.sh/install && \
    echo "bab8acfb046aac8c72407bdcce903957665d655d7acaa3e11c7c4616beae68dd  /tmp/bun-install.sh" | sha256sum -c - && \
    bash /tmp/bun-install.sh && \
    rm /tmp/bun-install.sh && \
    export PATH="/root/.bun/bin:$PATH" && \
    curl -fsSL -o /tmp/autohand-install.sh https://autohand.ai/install.sh && \
    echo "6c6321a005cf62f41a390ee64bc40142225383919621f84e7174ffa718a7fdce  /tmp/autohand-install.sh" | sha256sum -c - && \
    bash /tmp/autohand-install.sh && \
    rm /tmp/autohand-install.sh
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
