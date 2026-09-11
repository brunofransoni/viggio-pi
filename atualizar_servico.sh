#!/bin/bash
# Reinstala os arquivos de serviço systemd (viggio-portaria.service,
# viggio-kiosk.service) a partir do repositório.
#
# Necessário sempre que um desses arquivos mudar no repositório — o
# auto-update do main.py só puxa código (git pull), nunca reinstala os
# .service no systemd sozinho. Sem rodar isso, o Pi continua funcionando
# normalmente com o serviço antigo, só não ganha as mudanças novas do
# arquivo .service (ex.: o watchdog do systemd).
#
# Uso:
#   cd viggio-portaria
#   git pull
#   bash atualizar_servico.sh

set -e

INSTALL_DIR="$(pwd)"
INSTALL_USER="$(whoami)"

echo "Reinstalando serviços systemd (usuário: $INSTALL_USER, diretório: $INSTALL_DIR)..."

sed -e "s|__USER__|$INSTALL_USER|g" -e "s|__DIR__|$INSTALL_DIR|g" viggio-portaria.service | sudo tee /etc/systemd/system/viggio-portaria.service > /dev/null
sed -e "s|__USER__|$INSTALL_USER|g" -e "s|__DIR__|$INSTALL_DIR|g" viggio-kiosk.service | sudo tee /etc/systemd/system/viggio-kiosk.service > /dev/null

sudo systemctl daemon-reload
sudo systemctl restart viggio-portaria
sudo systemctl restart viggio-kiosk

echo ""
echo "=== Feito! Status do viggio-portaria: ==="
sudo systemctl status viggio-portaria --no-pager
