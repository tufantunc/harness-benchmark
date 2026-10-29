# docker/Dockerfile — single image with all tooling

# WhyCodes: upstream ships no linux-arm64 binary, so build the pinned tag from
# source with upstream's release command (release.yml). Bookworm builder =
# the runtime's glibc. rust-toolchain.toml (channel "stable" + components) is
# dropped so rustup keeps the image's pinned toolchain instead of fetching
# whatever stable is current.
FROM rust:1.97-bookworm AS whycodes-build
RUN git clone --depth 1 --branch v0.6.24 https://github.com/whycorporation/whycodes.git /src && \
    test "$(git -C /src rev-parse HEAD)" = "0811535499bbae9cb1bcaefd9a0ca2b94059bf3f" && \
    rm /src/rust-toolchain.toml
WORKDIR /src
RUN cargo build --release --locked -p whycodes-cli --features bundled-sqlite

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
    npm install -g --ignore-scripts @earendil-works/pi-coding-agent@1.0.1 && \
    npm install -g @jetbrains/junie && \
    npm install -g cline && \
    npm install -g @kilocode/cli && \
    npm install -g @charmland/crush && \
    npm install -g @deepseek-ai/dsh && \
    npm install -g @qwen-code/qwen-code && \
    npm install -g @github/copilot@1.0.97 && \
    npm install -g @anthropic-ai/claude-code@2.1.301

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
    echo "ca8ac11dac0e5df41a0b6d0845fc6600a3874b29d4abdab4af70ea898f5d81bb  /tmp/autohand-install.sh" | sha256sum -c - && \
    AUTOHAND_SKIP_COMPUTER_CONTROL_INSTALL=1 bash /tmp/autohand-install.sh && \
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
    echo "dcc19d498e14f96ab93828251b2848fde94cc2ab0bd6f9cad9baffbf7a229182  /tmp/grok-install.sh" | sha256sum -c - && \
    bash /tmp/grok-install.sh && \
    rm /tmp/grok-install.sh && \
    grok --version

# Install omp / oh-my-pi (pinned release binary, SHA256 from the GitHub release digest)
RUN curl -fsSL -o /usr/local/bin/omp \
    https://github.com/can1357/oh-my-pi/releases/download/v18.11.0/omp-linux-arm64 && \
    echo "299e0b63c482d78f00f2bae75000815ad6890cb6192cbc9f66c8d98e9ce70b80  /usr/local/bin/omp" | sha256sum -c - && \
    chmod +x /usr/local/bin/omp && \
    omp --version

# Install WrongStack wstack (pinned release binary, hash from official SHA256SUMS)
RUN curl -fsSL -o /usr/local/bin/wstack \
    https://github.com/WrongStack/WrongStack/releases/download/v1.3.0/wstack-linux-arm64 && \
    echo "b20074fd054a86481a129983430c9aedfed2924064a02bcd4298a9d45502f7ef  /usr/local/bin/wstack" | sha256sum -c - && \
    chmod +x /usr/local/bin/wstack && \
    wstack version

# Harnesses 17-19 sit after every existing install so adding them reuses the
# cached layers above (re-running the unpinned installers would drift the
# other harnesses' versions and trip their installer-script hash pins).

# Install OpenCode v2 (@opencode/cli) in its own prefix: it ships an `opencode`
# bin that would clash with v1's (opencode-ai) — the harness calls `opencode2`.
RUN npm install --prefix /opt/opencode2 @opencode/cli@2.2.0 && \
    ln -s /opt/opencode2/node_modules/.bin/opencode2 /usr/local/bin/opencode2 && \
    opencode2 --version

# Install Prime Agent (pinned release archive, SHA256 from the release's
# manifest.json). The archive's bundled install.sh --archive installs it
# offline from that file (launcher → ~/.local/bin) and pre-warms the Python
# kernel (uv + venv) so the first run needs no network for it.
RUN curl -fsSL -o /tmp/prime-agent-0.10.1-linux-arm64.tar.gz \
    https://github.com/PrimeIntellect-ai/prime-agent/releases/download/v0.10.1/prime-agent-0.10.1-linux-arm64.tar.gz && \
    echo "5af68c10a088538fd4990fd18778d8c7fe28c0491083dc069c5177f733770e91  /tmp/prime-agent-0.10.1-linux-arm64.tar.gz" | sha256sum -c - && \
    mkdir /tmp/prime-agent && \
    tar -xzf /tmp/prime-agent-0.10.1-linux-arm64.tar.gz -C /tmp/prime-agent && \
    sh /tmp/prime-agent/install.sh --archive /tmp/prime-agent-0.10.1-linux-arm64.tar.gz && \
    rm -rf /tmp/prime-agent /tmp/prime-agent-0.10.1-linux-arm64.tar.gz && \
    prime-agent --version

# Install WhyCodes (built from source in the whycodes-build stage above)
COPY --from=whycodes-build /src/target/release/whycodes /usr/local/bin/whycodes
RUN whycodes --version

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
