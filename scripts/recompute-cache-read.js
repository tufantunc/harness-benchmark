#!/usr/bin/env node
// scripts/recompute-cache-read.js
// Re-extract per-run cache-read tokens from captured responses with the
// proxy's current extractUsage (used by backfill-openai-cache.py).
// Usage: recompute-cache-read.js <results-dir>
// Output: one JSON line per run —
//   {artifact_path, request_count, responses, cache_read_tokens}
'use strict';

const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const { extractUsage } = require('../container/proxy.js');

const RESULTS = process.argv[2] || 'results';

// Captured bodies are the raw upstream bytes (content-encoding not recorded);
// same fallback order as analyze-proxy.js.
function decode(buf) {
    try { return zlib.brotliDecompressSync(buf); } catch {}
    try { return zlib.gunzipSync(buf); } catch {}
    return buf;
}

function dirs(p) {
    return fs.existsSync(p)
        ? fs.readdirSync(p, { withFileTypes: true }).filter(d => d.isDirectory()).map(d => d.name).sort()
        : [];
}

const artifacts = path.join(RESULTS, 'artifacts');
for (const harness of dirs(artifacts)) {
    for (const language of dirs(path.join(artifacts, harness))) {
        for (const exercise of dirs(path.join(artifacts, harness, language))) {
            for (const rep of dirs(path.join(artifacts, harness, language, exercise))) {
                const rel = ['artifacts', harness, language, exercise, rep].join('/');
                const capture = path.join(RESULTS, rel, 'captured-payloads');
                // A re-run copies its artifacts over the old directory, leaving
                // the old run's files wherever it wrote none: past its
                // request_count, and for requests whose response never
                // completed. The copy writes one run's files together, so
                // also skip responses older than its proxy-analysis.json.
                let requestCount = Infinity;
                let copiedAt = 0;
                try {
                    const analysis = path.join(RESULTS, rel, 'proxy-analysis.json');
                    requestCount = JSON.parse(fs.readFileSync(analysis)).request_count;
                    copiedAt = fs.statSync(analysis).mtimeMs - 60000;
                } catch {}
                const files = fs.existsSync(capture)
                    ? fs.readdirSync(capture).filter(f => {
                        const m = f.match(/^req-(\d+)-response\.raw$/);
                        return m && parseInt(m[1], 10) <= requestCount &&
                            fs.statSync(path.join(capture, f)).mtimeMs >= copiedAt;
                    })
                    : [];
                let cacheRead = 0;
                for (const f of files) {
                    const usage = extractUsage(decode(fs.readFileSync(path.join(capture, f))), '');
                    if (usage) cacheRead += usage.cache_read_tokens || 0;
                }
                console.log(JSON.stringify({
                    artifact_path: rel,
                    request_count: Number.isFinite(requestCount) ? requestCount : null,
                    responses: files.length,
                    cache_read_tokens: cacheRead,
                }));
            }
        }
    }
}
