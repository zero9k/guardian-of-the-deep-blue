#!/bin/bash
set -euo pipefail
umask 022
SRC=/home/weizek-deploy/app
WEB=/www/wwwroot/ocean.dnk.cc
API=/opt/weizek-api
BACKUP=/home/weizek-deploy/backups
mkdir -p "$BACKUP"
tmp=$(mktemp -d "$BACKUP/rollback.XXXXXXXX")
cp -a "$WEB/index.html" "$tmp/index.html" 2>/dev/null || true
cp -a "$WEB/assets" "$tmp/assets" 2>/dev/null || true
cp -a "$API/server.py" "$tmp/server.py" 2>/dev/null || true
rollback(){
  if [ -f "$tmp/index.html" ]; then cp -a "$tmp/index.html" "$WEB/index.html"; fi
  if [ -d "$tmp/assets" ]; then cp -a "$tmp/assets/." "$WEB/assets/"; fi
  if [ -f "$tmp/server.py" ]; then cp "$tmp/server.py" "$API/server.py"; fi
  chown -R www:www "$WEB/index.html" "$WEB/assets" "$API/server.py"
  systemctl restart weizek-api || true
}
trap 'rollback' ERR
/usr/bin/python3 -m py_compile "$SRC/backend/server.py"
install -m 644 "$SRC/backend/server.py" "$API/server.py"
rsync -a "$SRC/dist/" "$WEB/" --exclude='.user.ini' --exclude='.htaccess' --exclude='404.html'
chown -R www:www "$WEB/index.html" "$WEB/assets" "$API/server.py"
systemctl restart weizek-api
sleep 1
curl --fail --silent --max-time 8 http://127.0.0.1:18080/api/health >/dev/null
curl --fail --silent --max-time 8 -H 'Host: ocean.dnk.cc' http://127.0.0.1/ >/dev/null
trap - ERR
find "$BACKUP" -mindepth 1 -maxdepth 1 -type d -mtime +3 -exec rm -rf -- {} +
echo 'DEPLOY_OK'
