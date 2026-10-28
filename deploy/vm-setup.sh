#!/usr/bin/env bash
# Idempotently configure the Ubuntu VM for the Lost & Found Admin Panel.
set -euo pipefail

APP_DIR=/opt/lostfound
SERVICE_NAME=lostfound-admin
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ $EUID -ne 0 ]]; then
  echo "Run this script with sudo."
  exit 1
fi

read -r -p "Azure Key Vault URI (for example https://name.vault.azure.net/): " KEY_VAULT_URL
if [[ -z "$KEY_VAULT_URL" ]]; then
  echo "A Key Vault URI is required; no changes were made to application configuration."
  exit 1
fi

apt-get update
apt-get install -y ca-certificates curl gnupg git nginx openssl python3-venv python3-pip g++

# Install Microsoft ODBC Driver 18 only when it is not already available.
if ! odbcinst -q -d -n "ODBC Driver 18 for SQL Server" >/dev/null 2>&1; then
  install -d -m 0755 /etc/apt/keyrings
  curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /etc/apt/keyrings/microsoft-prod.gpg
  curl -fsSL https://packages.microsoft.com/config/ubuntu/24.04/prod.list -o /etc/apt/sources.list.d/microsoft-prod.list
  sed -i 's#/usr/share/keyrings/microsoft-prod.gpg#/etc/apt/keyrings/microsoft-prod.gpg#' /etc/apt/sources.list.d/microsoft-prod.list
  apt-get update
  ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc-dev
fi

# Deploy from the repository's configured remote so updates remain pullable.
REPO_URL="$(git -C "$SOURCE_DIR" config --get remote.origin.url || true)"
if [[ -z "$REPO_URL" ]]; then
  echo "The source checkout has no origin remote; cannot clone safely into $APP_DIR."
  exit 1
fi
if [[ -d "$APP_DIR/.git" ]]; then
  git -C "$APP_DIR" pull --ff-only
elif [[ -e "$APP_DIR" ]]; then
  echo "$APP_DIR already exists and is not the expected Git checkout; move it aside and retry."
  exit 1
else
  git clone "$REPO_URL" "$APP_DIR"
fi

python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

FLASK_SECRET_KEY="$(openssl rand -hex 32)"
install -m 0600 /dev/null /etc/lostfound.env
cat > /etc/lostfound.env <<EOF
APP_MODE=cloud
KEY_VAULT_URL=$KEY_VAULT_URL
FLASK_SECRET_KEY=$FLASK_SECRET_KEY
VISION_CAPTION=on
EOF

install -m 0644 "$APP_DIR/deploy/gunicorn-admin.service" "/etc/systemd/system/$SERVICE_NAME.service"
install -m 0644 "$APP_DIR/deploy/nginx-admin.conf" /etc/nginx/sites-available/lostfound-admin
ln -sfn /etc/nginx/sites-available/lostfound-admin /etc/nginx/sites-enabled/lostfound-admin
rm -f /etc/nginx/sites-enabled/default
chown -R www-data:www-data "$APP_DIR"

nginx -t
systemctl daemon-reload
systemctl enable --now "$SERVICE_NAME"
systemctl restart nginx
systemctl --no-pager status "$SERVICE_NAME"
echo "Admin Panel configured. Open http://$(hostname -I | awk '{print $1}') after allowing port 80 in the NSG."
