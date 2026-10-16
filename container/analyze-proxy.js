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
const zlib = require('zlib');

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

// Extract the model the API actually served from a captured response body
// (SSE chunks and plain JSON both carry "model":"..."). This is how silent
// upstream model aliasing (e.g. glm-5.2 requests served as glm-5.3) surfaces.
function servedModelFromBody(buf) {
    let body;
    try { body = zlib.brotliDecompressSync(buf).toString('utf8'); }
    catch {
        try { body = zlib.gunzipSync(buf).toString('utf8'); }
        catch { body = buf.toString('utf8'); }
    }
    const models = new Set();
    for (const m of body.matchAll(/"model":"([^"]+)"/g)) models.add(m[1]);
    return models;
}

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
let totalInput = 0;
let totalOutput = 0;
let maxToolCount = 0;
const systemHashes = new Set();
const toolsHashes = new Set();
let firstSystemTokens = 0;
let firstToolsTokens = 0;
let servedModels = new Set();
let requestModel = null;

for (const file of files) {
    const prefix = file.replace('-request.json', '');
    const reqPath = path.join(CAPTURE_DIR, file);
    const usagePath = path.join(CAPTURE_DIR, `${prefix}-usage.json`);

    let reqJson;
    try {
        reqJson = JSON.parse(fs.readFileSync(reqPath, 'utf8'));
    } catch { continue; }

    // Remember the requested model for the served-model fallback
    if (requestModel === null && typeof reqJson.model === 'string' && reqJson.model) {
        requestModel = reqJson.model;
    }

    // Extract system prompt and tools from request
    // Handles OpenAI chat (messages[0].role=system), OpenAI Responses
    // (instructions field), and Anthropic (system field) formats
    let system = '';
    let tools = [];

    if (typeof reqJson.system === 'string') {
        system = reqJson.system;
    } else if (Array.isArray(reqJson.system)) {
        system = reqJson.system.map(b => b.text || '').join('');
    } else if (typeof reqJson.instructions === 'string') {
        system = reqJson.instructions;
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

    const toolCount = Array.isArray(reqJson.tools) ? reqJson.tools.length : 0;
    const sysTokens = estimateTokens(system);

    // Track the request with the most tools (actual coding request, not warmup)
    if (toolCount > maxToolCount) {
        maxToolCount = toolCount;
        firstSystemTokens = sysTokens;
        firstToolsTokens = estimateTokens(tools);
    }

    // Only hash requests with significant tool counts (skip warmup/title-gen)
    if (toolCount > 3) {
        systemHashes.add(hash(system));
        toolsHashes.add(hash(tools));
    }

    // Read usage if available
    if (fs.existsSync(usagePath)) {
        try {
            const usage = JSON.parse(fs.readFileSync(usagePath, 'utf8'));
            totalCacheWrite += usage.cache_write_tokens || 0;
            totalCacheRead += usage.cache_read_tokens || 0;
            totalInput += usage.input_tokens || 0;
            totalOutput += usage.output_tokens || 0;
        } catch {}
    }

    // Collect served model from the first few captured responses
    const responsePath = path.join(CAPTURE_DIR, `${prefix}-response.raw`);
    if (servedModels.size === 0 && fs.existsSync(responsePath)) {
        try {
            for (const m of servedModelFromBody(fs.readFileSync(responsePath))) servedModels.add(m);
        } catch {}
    }
}

// Fallback for endpoints whose SSE emulation omits the model field entirely
// (z.ai's anthropic-compatible messages): take it from the first request
// body. Only fires when NO response carried a model — aliased OpenAI
// endpoints always do, so this never masks a silent upgrade. The source
// marker records that this value is client-claimed, not server-attested.
let servedModelSource = servedModels.size > 0 ? 'response' : 'none';
if (servedModels.size === 0 && requestModel) {
    servedModels.add(requestModel);
    servedModelSource = 'request';
}

const result = {
    input_tokens: totalInput,
    output_tokens: totalOutput,
    cache_write_tokens: totalCacheWrite,
    cache_read_tokens: totalCacheRead,
    system_prompt_tokens: firstSystemTokens,
    tool_schema_tokens: firstToolsTokens,
    prefix_stable: systemHashes.size <= 1 && toolsHashes.size <= 1,
    prefix_variants: Math.max(systemHashes.size, toolsHashes.size),
    request_count: files.length,
    served_model: [...servedModels].sort().join('+'),
    served_model_source: servedModelSource,
};

console.log(JSON.stringify(result, null, 2));
