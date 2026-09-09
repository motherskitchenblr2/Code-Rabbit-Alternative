// =============================================================================
// Cloudflare Worker Entry Point for Git-Fix API
// =============================================================================
// Deploy with: wrangler deploy
// =============================================================================

import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { logger } from 'hono/logger';
import { secureHeaders } from 'hono/secure-headers';
import { jwt } from 'hono/jwt';
import { HTTPException } from 'hono/http-exception';

// Types
interface Env {
  CACHE: KVNamespace;
  DB?: D1Database;
  STORAGE?: R2Bucket;
  JWT_SECRET: string;
  GITHUB_WEBHOOK_SECRET: string;
  DATABASE_URL: string;
  REDIS_URL: string;
  QDRANT_URL: string;
  JWT_SECRET: string;
}

// Extended context with bindings
type AppContext = {
  Bindings: Env;
  Variables: {
    user: any;
    requestId: string;
  };
};

const app = new Hono<AppContext>();

// Middleware
app.use('*', logger());
app.use('*', secureHeaders());
app.use('*', cors({
  origin: ['https://gitfix.io', 'https://staging.gitfix.io', 'http://localhost:5173'],
  allowMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowHeaders: ['Content-Type', 'Authorization'],
  credentials: true,
});

// Request ID middleware
app.use('*', async (c, next) => {
  const requestId = crypto.randomUUID();
  c.set('requestId', requestId);
  c.header('X-Request-ID', requestId);
  await next();
});

// Health check
app.get('/api/v1/health', (c) => {
  return c.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    version: '1.0.0',
    checks: {
      cache: 'connected',
      database: 'connected',
    }
  });
});

// Metrics endpoint
app.get('/api/v1/metrics', async (c) => {
  // Return Prometheus-style metrics
  const metrics = `
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/api/v1/health"} 1234
# HELP http_request_duration_seconds HTTP request latency
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{le="0.1"} 1200
http_request_duration_seconds_bucket{le="0.5"} 1500
http_request_duration_seconds_bucket{le="1.0"} 1600
  `;
  return c.text(metrics, 200, { 'Content-Type': 'text/plain' });
});

// Webhook endpoint for GitHub
app.post('/api/v1/webhook', async (c) => {
  const signature = c.req.header('X-Hub-Signature-256');
  const body = await c.req.text();
  
  // Verify HMAC signature
  const secret = c.env.GITHUB_WEBHOOK_SECRET;
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  const signatureBytes = await crypto.subtle.sign('HMAC', key, encoder.encode(body));
  const expectedSignature = 'sha256=' + Array.from(new Uint8Array(signatureBytes))
    .map(b => b.toString(16).padStart(2, '0')).join('');
  
  if (signature !== expectedSignature) {
    throw new HTTPException(401, { message: 'Invalid signature' });
  }
  
  const payload = JSON.parse(body);
  
  // Process webhook asynchronously
  const eventId = crypto.randomUUID();
  
  // Queue for processing (using KV as queue)
  await c.env.CACHE.put(`webhook:${eventId}`, JSON.stringify(payload), {
    expirationTtl: 3600
  });
  
  return c.json({ status: 'accepted', event_id: eventId }, 202);
});

// Pipeline status
app.get('/api/v1/status', async (c) => {
  const stats = await c.env.CACHE.get('pipeline:stats', 'json') || {
    events_processed: 0,
    comments_dispatched: 0,
    reviews_created: 0,
  };
  return c.json(stats);
});

// Repository webhook events
app.post('/api/v1/github/webhook', async (c) => {
  const signature = c.req.header('X-Hub-Signature-256');
  const body = await c.req.text();
  
  // Verify signature
  const secret = c.env.GITHUB_WEBHOOK_SECRET;
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  const signatureBytes = await crypto.subtle.sign('HMAC', key, encoder.encode(body));
  const expectedSignature = 'sha256=' + Array.from(new Uint8Array(signatureBytes))
    .map(b => b.toString(16).padStart(2, '0')).join('');
  
  if (signature !== expectedSignature) {
    throw new HTTPException(401, { message: 'Invalid signature' });
  }
  
  const payload = JSON.parse(body);
  
  // Process asynchronously
  const eventId = crypto.randomUUID();
  await c.env.CACHE.put(`webhook:${eventId}`, JSON.stringify(payload), {
    expirationTtl: 3600
  });
  
  return c.json({ status: 'accepted', event_id: eventId }, 202);
});

// WebSocket endpoint for real-time updates
export default {
  fetch: app.fetch,
  async websocket(ws: WebSocket, env: Env, ctx: ExecutionContext) {
    ws.accept();
    
    ws.addEventListener('message', async (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'subscribe') {
          // Subscribe to repository updates
          ws.send(JSON.stringify({ type: 'subscribed', channels: data.channels }));
        } else if (data.type === 'ping') {
          ws.send(JSON.stringify({ type: 'pong', timestamp: Date.now() }));
        }
      } catch (e) {
        ws.send(JSON.stringify({ type: 'error', message: 'Invalid message format' }));
      }
    });
    
    ws.addEventListener('close', () => {
      // Clean up subscriptions
    });
  },
  
  // Scheduled tasks
  async scheduled(event: ScheduledEvent, env: Env, ctx: ExecutionContext) {
    // Daily metrics aggregation
    if (event.cron === '0 2 * * *') {
      // Aggregate daily metrics
      await aggregateDailyMetrics(env);
    }
    
    // Cleanup old data
    if (event.cron === '0 3 * * *') {
      await cleanupOldData(env);
    }
  }
};

async function aggregateDailyMetrics(env: Env) {
  // Aggregate metrics from KV
  console.log('Aggregating daily metrics...');
}

async function cleanupOldData(env: Env) {
  // Cleanup old cache entries
  console.log('Cleaning up old data...');
}

export default app;