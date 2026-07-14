#!/usr/bin/env node
// container/proxy.js
// Logging reverse proxy: captures request payloads and response usage.
// Flow: agent CLI → proxy (localhost:8080) → real model API
//
// Captures per request:
//   <req-id>-request.json  — full request payload (system prompt, tools, messages)
//   <req-id>-response.raw  — raw response bytes
//   <req-id>-usage.json    — extracted usage (input/output/cache_write/cache_read)
'use strict';

const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const { URL } = require('url');

const UPSTREAM = process.env.UPSTREAM_URL;
const CAPTURE_DIR = process.env.CAPTURE_DIR || '/output/captured-payloads';
const PORT = parseInt(process.env.PROXY_PORT || '8080', 10);

if (!UPSTREAM) {
    console.error('[proxy] UPSTREAM_URL not set');
    process.exit(1);
}

fs.mkdirSync(CAPTURE_DIR, { recursive: true });

let requestCount = 0;

function extractUsage(respBody, contentType) {
    const body = respBody.toString('utf8');
    const ct = contentType || '';

    if (ct.includes('application/json')) {
        try { return extractUsageFromJson(JSON.parse(body)); } catch { return null; }
    }
    if (ct.includes('text/event-stream') || body.includes('data: ')) {
        return extractUsageFromSse(body);
    }
    try { return extractUsageFromJson(JSON.parse(body)); } catch { return null; }
}

function extractUsageFromJson(json) {
    const u = json.usage;
    if (!u) return null;
    return {
        input_tokens: u.prompt_tokens || u.input_tokens || 0,
        output_tokens: u.completion_tokens || u.output_tokens || 0,
        cache_read_tokens: u.cache_read_input_tokens || u.cache_read || 0,
        cache_write_tokens: u.cache_creation_input_tokens || u.cache_write || 0,
    };
}

function extractUsageFromSse(body) {
    let usage = null;
    let outputTokensFromDelta = 0;

    for (const line of body.split('\n')) {
        if (!line.startsWith('data: ')) continue;
        const data = line.slice(6).trim();
        if (data === '[DONE]') continue;

        try {
            const json = JSON.parse(data);

            // Anthropic: message_start has input+cache, message_delta has output
            if (json.type === 'message_start' && json.message && json.message.usage) {
                const u = json.message.usage;
                usage = {
                    input_tokens: u.input_tokens || 0,
                    output_tokens: u.output_tokens || 0,
                    cache_read_tokens: u.cache_read_input_tokens || 0,
                    cache_write_tokens: u.cache_creation_input_tokens || 0,
                };
            }
            if (json.type === 'message_delta' && json.usage) {
                outputTokensFromDelta = json.usage.output_tokens || 0;
            }

            // OpenAI: usage in final chunk
            if (json.usage) {
                const u = json.usage;
                usage = {
                    input_tokens: u.prompt_tokens || u.input_tokens || 0,
                    output_tokens: u.completion_tokens || u.output_tokens || 0,
                    cache_read_tokens: u.cache_read_input_tokens || u.cache_read || 0,
                    cache_write_tokens: u.cache_creation_input_tokens || u.cache_write || 0,
                };
            }
        } catch {}
    }

    if (usage && outputTokensFromDelta > 0) {
        usage.output_tokens = outputTokensFromDelta;
    }
    return usage;
}

const server = http.createServer((clientReq, clientRes) => {
    const chunks = [];
    clientReq.on('data', chunk => chunks.push(chunk));
    clientReq.on('end', () => {
        const reqBody = Buffer.concat(chunks);
        requestCount++;
        const reqId = `req-${String(requestCount).padStart(4, '0')}`;

        fs.writeFileSync(path.join(CAPTURE_DIR, `${reqId}-request.json`), reqBody);

        const upstream = new URL(UPSTREAM.replace(/\/$/, '') + clientReq.url);
        const isHttps = upstream.protocol === 'https:';
        const lib = isHttps ? https : http;

        const headers = { ...clientReq.headers };
        headers['host'] = upstream.host;
        delete headers['content-length'];
        delete headers['transfer-encoding'];
        headers['content-length'] = reqBody.length;

        const options = {
            method: clientReq.method,
            hostname: upstream.hostname,
            port: upstream.port || (isHttps ? 443 : 80),
            path: upstream.pathname + upstream.search,
            headers: headers,
        };

        const proxyReq = lib.request(options, (proxyRes) => {
            const respChunks = [];
            clientRes.writeHead(proxyRes.statusCode, proxyRes.headers);

            proxyRes.on('data', chunk => {
                respChunks.push(chunk);
                clientRes.write(chunk);
            });

            proxyRes.on('end', () => {
                clientRes.end();
                const respBody = Buffer.concat(respChunks);

                fs.writeFileSync(path.join(CAPTURE_DIR, `${reqId}-response.raw`), respBody);

                const usage = extractUsage(respBody, proxyRes.headers['content-type']);
                if (usage) {
                    fs.writeFileSync(
                        path.join(CAPTURE_DIR, `${reqId}-usage.json`),
                        JSON.stringify(usage, null, 2)
                    );
                }
            });
        });

        proxyReq.on('error', (e) => {
            console.error(`[proxy] error for ${reqId}: ${e.message}`);
            if (!clientRes.headersSent) {
                clientRes.writeHead(502, { 'content-type': 'application/json' });
                clientRes.end(JSON.stringify({ error: { message: e.message } }));
            }
        });

        proxyReq.write(reqBody);
        proxyReq.end();
    });
});

server.listen(PORT, '127.0.0.1', () => {
    console.error(`[proxy] listening on http://127.0.0.1:${PORT} -> ${UPSTREAM}`);
});
