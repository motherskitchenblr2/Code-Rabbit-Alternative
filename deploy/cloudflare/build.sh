#!/usr/bin/env bash
# =============================================================================
# Cloudflare Pages Build Script for Git-Fix
# =============================================================================
# This script builds the frontend for Cloudflare Pages deployment
# =============================================================================

set -euo pipefail

echo "☁️ Cloudflare Pages Build Starting..."

# Install dependencies
echo "📦 Installing dependencies..."
cd frontend
npm ci --prefer-offline --no-audit --no-fund

# Build for production
echo "🏗️ Building for production..."
npm run build

# Verify build output
if [ ! -d "dist" ]; then
    echo "❌ Build failed: dist directory not found"
    exit 1
fi

# Copy _redirects for SPA routing
cat > dist/_redirects << 'EOF'
# SPA routing
/* /index.html 200

# API routes
/api/* https://api.gitfix.io/api/:splat 200
/ws/* wss://api.gitfix.io/ws/:splat 200
EOF

# Add security headers
cat > dist/_headers << 'EOF'
/*
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  X-XSS-Protection: 1; mode=block
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://unpkg.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' ws: wss: https://api.gitfix.io;

/assets/*
  Cache-Control: public, max-age=31536000, immutable

/api/*
  Access-Control-Allow-Origin: *
  Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
  Access-Control-Allow-Headers: Content-Type, Authorization
EOF

# Generate _routes.json for SPA
cat > dist/_routes.json << 'EOF'
{
  "version": 1,
  "include": ["/*"],
  "exclude": ["/api/*", "/ws/*"]
}
EOF

echo "✅ Cloudflare Pages build complete"
echo "📁 Output: frontend/dist"
ls -la dist/
EOF
chmod +x /data/data/com.termux/files/home/Code-Rabbit-Alternative/deploy/cloudflare/build.sh