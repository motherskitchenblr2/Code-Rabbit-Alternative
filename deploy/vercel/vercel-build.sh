#!/usr/bin/env bash
# =============================================================================
# Vercel Build Script for Git-Fix
# =============================================================================
# This script runs during Vercel deployment to build the frontend and prepare
# the Python API for serverless functions.
# =============================================================================

set -euo pipefail

echo "🔨 Vercel Build Starting..."

# Install frontend dependencies
echo "📦 Installing frontend dependencies..."
cd frontend
npm ci --prefer-offline --no-audit --no-fund

# Build frontend
echo "🏗️ Building frontend..."
npm run build

# Verify build output
if [ ! -d "dist" ]; then
    echo "❌ Build failed: dist directory not found"
    exit 1
fi

echo "✅ Frontend build complete"

# Prepare Python API for serverless functions
echo "🐍 Preparing Python API..."
cd ..

# Create serverless function entry point
cat > api/index.py << 'EOF'
from app import app
from mangum import Mangum

handler = Mangum(app, lifespan="off")
EOF

# Create requirements for serverless
cat > api/requirements.txt << 'EOF'
flask>=3.0.0
flask-cors>=4.0.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
httpx>=0.25.0
mangum>=0.17.0
EOF

# Install Python dependencies for serverless
pip install --no-cache-dir -r api/requirements.txt -t api/

echo "✅ Vercel build complete"
EOF
chmod +x /data/data/com.termux/files/home/Code-Rabbit-Alternative/deploy/vercel/vercel-build.sh