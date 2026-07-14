#!/usr/bin/env node
// container/analyze-proxy.js
// Post-hoc analysis of captured proxy payloads.
// Extracts cache metrics + prefix stability from captured request/response data.
// Usage: analyze-proxy.js <capture-dir>
// Output: JSON to stdout
'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const CAPTURE_DIR = process.argv[2] || '/output/captured-payloads';

function hash(obj) {
    return crypto.createHash('sha256')
        .update(JSON.stringify(obj))
        .digest('hex').slice(0, 16);
}

function estimateTokens(val) {
    if (val === null || val === undefined) return 0;
    const str = typeof val === 'string' ? val : JSON.stringify(val);
    return Math.ceil(str.length / 4);
}

const files = fs.existsSync(CAPTURE_DIR)
    ? fs.readdirSync(CAPTURE_DIR).filter(f => f.endsWith('-request.json')).sort()
    : [];

if (files.length === 0) {
    console.log(JSON.stringify({
        cache_write_tokens: 0,
        cache_read_tokens: 0,
        system_prompt_tokens: 0,
        tool_schema_tokens: 0,
        prefix_stable: true,
        prefix_variants: 0,
        request_count: 0,
    }));
    process.exit(0);
}

let totalCacheWrite = 0;
let totalCacheRead = 0;
const systemHashes = new Set();
const toolsHashes = new Set();
let firstSystemTokens = 0;
let firstToolsTokens = 0;

for (const file of files) {
    const prefix = file.replace('-request.json', '');
    const reqPath = path.join(CAPTURE_DIR, file);
    const usagePath = path.join(CAPTURE_DIR, `${prefix}-usage.json`);

    let reqJson;
    try {
        reqJson = JSON.parse(fs.readFileSync(reqPath, 'utf8'));
    } catch { continue; }

    // Extract system prompt and tools from request
    // Handles both OpenAI (messages[0].role=system) and Anthropic (system field) formats
    let system = '';
    let tools = [];

    if (typeof reqJson.system === 'string') {
        system = reqJson.system;
    } else if (Array.isArray(reqJson.system)) {
        system = reqJson.system.map(b => b.text || '').join('');
    } else if (reqJson.messages) {
        const sysMsg = reqJson.messages.find(m => m.role === 'system');
        if (sysMsg) {
            system = typeof sysMsg.content === 'string'
                ? sysMsg.content
                : (Array.isArray(sysMsg.content) ? sysMsg.content.map(b => b.text || '').join('') : '');
        }
    }

    if (Array.isArray(reqJson.tools)) {
        tools = reqJson.tools;
    }

    systemHashes.add(hash(system));
    toolsHashes.add(hash(tools));

    if (firstSystemTokens === 0) {
        firstSystemTokens = estimateTokens(system);
        firstToolsTokens = estimateTokens(tools);
    }

    // Read usage if available
    if (fs.existsSync(usagePath)) {
        try {
            const usage = JSON.parse(fs.readFileSync(usagePath, 'utf8'));
            totalCacheWrite += usage.cache_write_tokens || 0;
            totalCacheRead += usage.cache_read_tokens || 0;
        } catch {}
    }
}

const result = {
    cache_write_tokens: totalCacheWrite,
    cache_read_tokens: totalCacheRead,
    system_prompt_tokens: firstSystemTokens,
    tool_schema_tokens: firstToolsTokens,
    prefix_stable: systemHashes.size <= 1 && toolsHashes.size <= 1,
    prefix_variants: Math.max(systemHashes.size, toolsHashes.size),
    request_count: files.length,
};

console.log(JSON.stringify(result, null, 2));
