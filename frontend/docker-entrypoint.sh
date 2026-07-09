#!/bin/sh
set -e
API_URL="${API_URL:-http://localhost:8000}"
cat > /usr/share/nginx/html/config.js <<EOF
window.__API_URL__ = "${API_URL}";
EOF
exec "$@"
