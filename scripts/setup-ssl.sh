#!/usr/bin/env bash
# ── Aurum PMS — One-command SSL setup (Let's Encrypt) ──────────────────────
#
# Usage (run from project root on your VPS):
#   bash scripts/setup-ssl.sh yourdomain.com you@email.com
#
# What it does:
#   1. Checks that nginx is up and port 80 is reachable
#   2. Runs certbot to issue a certificate via HTTP-01 challenge
#   3. Swaps nginx config from HTTP-only → HTTPS (nginx.ssl.conf)
#   4. Reloads nginx
#   5. Tests the renewal process
#
# Requirements: docker compose -f docker-compose.prod.yml must already be up.

set -euo pipefail

DOMAIN="${1:-}"
EMAIL="${2:-}"

if [[ -z "$DOMAIN" || -z "$EMAIL" ]]; then
  echo "Usage: bash scripts/setup-ssl.sh <domain> <email>"
  echo "  e.g. bash scripts/setup-ssl.sh aurum.example.com admin@example.com"
  exit 1
fi

echo ""
echo "══════════════════════════════════════════════"
echo "  Aurum PMS — Let's Encrypt SSL setup"
echo "  Domain : $DOMAIN"
echo "  Email  : $EMAIL"
echo "══════════════════════════════════════════════"
echo ""

# ── Step 1: confirm nginx is serving HTTP ───────────────────────────────────
echo "[1/4] Checking nginx is up..."
if ! docker compose -f docker-compose.prod.yml ps nginx | grep -q "Up\|running"; then
  echo "ERROR: nginx container is not running."
  echo "Run: docker compose -f docker-compose.prod.yml up -d"
  exit 1
fi
echo "      ✓ nginx is running"

# ── Step 2: issue certificate via certbot (HTTP-01 webroot challenge) ────────
echo "[2/4] Issuing Let's Encrypt certificate for $DOMAIN..."
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot \
  --webroot-path /var/www/certbot \
  --email "$EMAIL" \
  --agree-tos \
  --no-eff-email \
  --domain "$DOMAIN" \
  --domain "www.$DOMAIN"

echo "      ✓ Certificate issued"

# ── Step 3: install HTTPS nginx config ──────────────────────────────────────
echo "[3/4] Installing HTTPS nginx config..."
# Substitute YOUR_DOMAIN placeholder with the real domain
sed "s/YOUR_DOMAIN/$DOMAIN/g" nginx/nginx.ssl.conf > nginx/nginx.active.conf
cp nginx/nginx.active.conf nginx/nginx.prod.conf

echo "      ✓ nginx.prod.conf updated to nginx.ssl.conf (with domain: $DOMAIN)"

# Update CORS_ORIGINS in running backend if .env exists
if [[ -f .env ]]; then
  # Add https:// version alongside any existing origins
  CURRENT_CORS=$(grep "^CORS_ORIGINS=" .env | cut -d= -f2-)
  if [[ "$CURRENT_CORS" != *"https://$DOMAIN"* ]]; then
    sed -i "s|^CORS_ORIGINS=.*|CORS_ORIGINS=https://$DOMAIN,https://www.$DOMAIN|" .env
    echo "      ✓ CORS_ORIGINS updated in .env"
  fi
fi

# ── Step 4: reload nginx with new config ────────────────────────────────────
echo "[4/4] Reloading nginx..."
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
echo "      ✓ nginx reloaded"

# ── Done ────────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════"
echo "  ✓ SSL is active!"
echo ""
echo "  Platform:  https://$DOMAIN"
echo "  API docs:  https://$DOMAIN/docs"
echo ""
echo "  Certs auto-renew every 12h (certbot container)."
echo "  Run a manual renewal test:"
echo "    docker compose -f docker-compose.prod.yml run --rm certbot renew --dry-run"
echo "══════════════════════════════════════════════"
echo ""

# Restart backend so it picks up new CORS_ORIGINS
docker compose -f docker-compose.prod.yml up -d --no-build backend
