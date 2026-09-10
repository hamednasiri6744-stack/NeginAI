import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const registryPath = path.resolve(here, '..', 'local-capabilities.json');
const registry = JSON.parse(fs.readFileSync(registryPath, 'utf8').replace(/^\uFEFF/, ''));

const args = Object.fromEntries(process.argv.slice(2).map((x) => {
  const i = x.indexOf('=');
  return i > 0 ? [x.slice(0, i).replace(/^--/, ''), x.slice(i + 1)] : [x.replace(/^--/, ''), 'true'];
}));

const serviceName = args.service;
const method = args.method || 'tools/list';
if (!serviceName || !registry.services[serviceName]) throw new Error('known --service required');
const service = registry.services[serviceName];
const endpoint = new URL(service.endpoint);
if (!['127.0.0.1', 'localhost'].includes(endpoint.hostname)) throw new Error('loopback_only');

function credentialFor(svc) {
  if (svc.tokenEnv && process.env[svc.tokenEnv]) return process.env[svc.tokenEnv];
  if (svc.tokenConfig) {
    const cfg = JSON.parse(fs.readFileSync(svc.tokenConfig, 'utf8').replace(/^\uFEFF/, ''));
    const value = cfg[svc.tokenField || 'bearer_token'];
    if (value) return String(value);
  }
  return '';
}

function redact(value) {
  if (Array.isArray(value)) return value.map(redact);
  if (!value || typeof value !== 'object') return value;
  const out = {};
  for (const [k, v] of Object.entries(value)) {
    out[k] = /token|secret|password|authorization|cookie|api[-_]?key/i.test(k) ? '[REDACTED]' : redact(v);
  }
  return out;
}

const headers = { 'content-type': 'application/json' };
const credential = credentialFor(service);
if (credential) headers.authorization = `Bearer ${credential}`;

let params = {};
if (args.params) params = JSON.parse(args.params);
if (method === 'tools/call') {
  if (!args.tool) throw new Error('--tool required for tools/call');
  const isFigmaMutation = serviceName === 'figma-x' && args.tool === 'figma_x_apply_operations';
  if (isFigmaMutation && args.ownerApproved !== 'true') throw new Error('figma_mutation_requires_--ownerApproved=true');
  params = { name: args.tool, arguments: params };
}

const body = { jsonrpc: '2.0', id: Date.now(), method, params };
const response = await fetch(endpoint, { method: 'POST', headers, body: JSON.stringify(body) });
const text = await response.text();
let payload;
try { payload = text ? JSON.parse(text) : {}; } catch { payload = { raw: text.slice(0, 2000) }; }
const safe = redact({ httpStatus: response.status, service: serviceName, response: payload });
console.log(JSON.stringify(safe, null, 2));
if (!response.ok) process.exitCode = 2;
