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

# Install Kimi Code CLI (curl installer — SHA256 pinned)
RUN curl -fsSL -o /tmp/kimi-install.sh https://code.kimi.com/kimi-code/install.sh && \
    echo "624e4857a73f587961b51ef91c9bf28229f886a0817e96935e88dfd09445faab  /tmp/kimi-install.sh" | sha256sum -c - && \
    bash /tmp/kimi-install.sh && \
    rm /tmp/kimi-install.sh

# Install Bun (SHA256 pinned) then AutoHand Code CLI (SHA256 pinned)
RUN curl -fsSL -o /tmp/bun-install.sh https://bun.sh/install && \
    echo "04882bf41679d49d9af108657a1e5515bf04fdf2940d12c0d0b1e5d79dc53be8  /tmp/bun-install.sh" | sha256sum -c - && \
    bash /tmp/bun-install.sh && \
    rm /tmp/bun-install.sh && \
    export PATH="/root/.bun/bin:$PATH" && \
    curl -fsSL -o /tmp/autohand-install.sh https://autohand.ai/install.sh && \
    echo "dd30c1a575e78bf1b8d0932beb9133fbc60f8644db5903ca74e4f210b680f6cb  /tmp/autohand-install.sh" | sha256sum -c - && \
    bash /tmp/autohand-install.sh && \
    rm /tmp/autohand-install.sh
# Install Factory Droid (SHA256 pinned)
RUN curl -fsSL -o /tmp/droid-cli.sh https://app.factory.ai/cli && \
    echo "78d54387be076e8eb2aade5fe97c9220f161a1dcf91f0d209b81ff807d91f9b0  /tmp/droid-cli.sh" | sha256sum -c - && \
    sh /tmp/droid-cli.sh && \
    rm /tmp/droid-cli.sh

# Install Goose CLI (SHA256 pinned, non-interactive)
RUN curl -fsSL -o /tmp/goose-cli.sh \
    https://github.com/aaif-goose/goose/releases/download/stable/download_cli.sh && \
    echo "ab5ae40513348ec4e6047cc7338040aab2df5246800c111d22065766ba6013f0  /tmp/goose-cli.sh" | sha256sum -c - && \
    CONFIGURE=false bash /tmp/goose-cli.sh < /dev/null && \
    rm /tmp/goose-cli.sh
ENV PATH="/root/.local/bin:/root/.kimi-code/bin:/root/.bun/bin:${PATH}"

# Install Grok Build (curl installer, not npm)
# SHA256 pins the installer script for reproducibility — update both when upgrading grok
RUN curl -fsSL -o /tmp/grok-install.sh https://x.ai/cli/install.sh && \
    echo "43d0943123edade1383a476a4f778674877acee7c1f98a00f094c4a0f7349321  /tmp/grok-install.sh" | sha256sum -c - && \
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
