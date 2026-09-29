# docker/Dockerfile — single image with all tooling
FROM node:22-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    git jq curl ca-certificates unzip \
    build-essential python3-dev \
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
    npm install -g @kilocode/cli && \
    npm install -g @charmland/crush && \
    npm install -g @deepseek-ai/dsh

# codex: removed — requires Responses API (wire_api=chat removed from codex
# in Feb 2026, still rejected in 0.159.0) and no available upstream serves
# /responses (BigModel and Z.ai both 404 with real key). Adapter parked in
# harnesses/codex/ pending a Responses→Chat bridge or platform support.

# Install Kimi Code CLI (curl installer — SHA256 pins the installer script for
# reproducibility; update the pin (after verifying the newly served script) when
# upstream changes it. KIMI_VERSION pins the binary version — update on upgrade.)
RUN curl -fsSL -o /tmp/kimi-install.sh https://code.kimi.com/kimi-code/install.sh && \
    echo "270a86f2d2304529b6d8a3783fca9534874ebaeecb6cfcc1aebcdb6ce20ae1d7  /tmp/kimi-install.sh" | sha256sum -c - && \
    KIMI_VERSION=0.38.0 bash /tmp/kimi-install.sh && \
    rm /tmp/kimi-install.sh

# Install Bun (SHA256 pinned) then AutoHand Code CLI (SHA256 pinned)
RUN curl -fsSL -o /tmp/bun-install.sh https://bun.sh/install && \
    echo "04882bf41679d49d9af108657a1e5515bf04fdf2940d12c0d0b1e5d79dc53be8  /tmp/bun-install.sh" | sha256sum -c - && \
    bash /tmp/bun-install.sh && \
    rm /tmp/bun-install.sh && \
    export PATH="/root/.bun/bin:$PATH" && \
    curl -fsSL -o /tmp/autohand-install.sh https://autohand.ai/install.sh && \
    echo "e82ab8ffa3f63feb4acc25fb07b28dce4052305a2a68369a18d0c6c816df4d6a  /tmp/autohand-install.sh" | sha256sum -c - && \
    bash /tmp/autohand-install.sh && \
    rm /tmp/autohand-install.sh

# droid: removed — requires Factory auth even for BYOK (spec 2026-07-29, decision 3)

# Install Goose CLI (SHA256 pinned, non-interactive)
RUN curl -fsSL -o /tmp/goose-cli.sh \
    https://github.com/aaif-goose/goose/releases/download/stable/download_cli.sh && \
    echo "710f208cf0225ac330f71cc1540d36b10a6be7a850334b5ec4770fe96fbc57c4  /tmp/goose-cli.sh" | sha256sum -c - && \
    CONFIGURE=false bash /tmp/goose-cli.sh < /dev/null && \
    rm /tmp/goose-cli.sh
ENV PATH="/root/.local/bin:/root/.kimi-code/bin:/root/.bun/bin:${PATH}"

# Install Grok Build (curl installer, not npm)
# SHA256 pins the installer script for reproducibility — update both when upgrading grok
RUN curl -fsSL -o /tmp/grok-install.sh https://x.ai/cli/install.sh && \
    echo "7fd6fdc75d9418b2e58356726fcbf1ae849416f773925da07d0ccc7a60d3e791  /tmp/grok-install.sh" | sha256sum -c - && \
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
