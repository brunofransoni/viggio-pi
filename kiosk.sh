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
  "https://app.viggiotech.com.br" &

# Manter o script rodando
wait
