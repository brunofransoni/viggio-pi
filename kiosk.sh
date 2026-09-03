#!/bin/bash
# Aguarda o sistema inicializar completamente
sleep 10

# Configurar display
export DISPLAY=:0

# Desabilitar proteção de tela
xset s off
xset -dpms
xset s noblank

# Ocultar cursor do mouse após 5 segundos de inatividade
unclutter -idle 5 -root &

# Lê pwa_url/api_key de config.json e anexa a api_key como ?deviceKey= —
# o backend usa isso pra nunca expirar essa sessão por inatividade (ver
# resolverEstaPermanente em auth.service.js). Sem api_key configurada, abre
# a URL normal e o porteiro loga com email/senha como em qualquer device.
URL=$(python3 -c "
import json, urllib.parse
try:
    with open('config.json') as f:
        cfg = json.load(f)
except Exception:
    cfg = {}
pwa_url = cfg.get('pwa_url', 'https://app.viggiotech.com.br')
api_key = cfg.get('api_key', '')
print(f'{pwa_url}?deviceKey={urllib.parse.quote(api_key)}' if api_key else pwa_url)
")

# O binário do pacote chromium-browser varia por distro/versão do Debian —
# em alguns o comando é "chromium-browser", em outros só "chromium".
if command -v chromium-browser >/dev/null 2>&1; then
  CHROMIUM=chromium-browser
elif command -v chromium >/dev/null 2>&1; then
  CHROMIUM=chromium
else
  echo "Nenhum binário do chromium encontrado (chromium-browser/chromium)" >&2
  exit 1
fi

# Abrir Chromium em modo kiosk — tela cheia, sem barra, sem botões
"$CHROMIUM" \
  --kiosk \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-features=TranslateUI \
  --no-first-run \
  --start-fullscreen \
  --window-size=1024,600 \
  --touch-events=enabled \
  --enable-touch-drag-drop \
  "$URL" &

# Manter o script rodando
wait
