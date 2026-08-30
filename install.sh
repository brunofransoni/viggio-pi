#!/bin/bash
# Viggio Tech — Instalação completa no Raspberry Pi 5
# Rodar de dentro do diretório clonado, como o usuário normal (não root/sudo):
#   cd viggio-portaria && bash install.sh

set -e
echo "=== Viggio Tech — Instalação da Portaria ==="

INSTALL_DIR="$(pwd)"
INSTALL_USER="$(whoami)"
echo "Instalando em $INSTALL_DIR como usuário $INSTALL_USER"

# 1. Atualizar sistema
sudo apt-get update && sudo apt-get upgrade -y

# 2. Instalar dependências do sistema
sudo apt-get install -y \
  python3 python3-pip python3-venv \
  chromium-browser \
  unclutter \
  alsa-utils \
  i2c-tools \
  swig

# libgpiod teve o nome do pacote runtime trocado entre versões do Debian
# (libgpiod2 em Bookworm e anteriores, libgpiod3 a partir do Trixie, por
# causa de um bump de ABI incompatível) — tenta os dois.
sudo apt-get install -y libgpiod2 || sudo apt-get install -y libgpiod3

# 3. Habilitar I2C no Pi 5
sudo raspi-config nonint do_i2c 0
echo "I2C habilitado"

# 4. Criar ambiente virtual Python
python3 -m venv "$INSTALL_DIR/venv"
source "$INSTALL_DIR/venv/bin/activate"

# 5. Instalar dependências Python
pip install -r requirements.txt

# 6. Criar config inicial a partir do template
if [ ! -f "$INSTALL_DIR/config.json" ]; then
  cp config.example.json "$INSTALL_DIR/config.json"
  echo "⚠️  Edite $INSTALL_DIR/config.json e adicione a API key!"
fi

# 7. Permissão de execução
chmod +x kiosk.sh

# 8. Instalar serviços systemd (substitui usuário/diretório reais nos templates)
sed -e "s|__USER__|$INSTALL_USER|g" -e "s|__DIR__|$INSTALL_DIR|g" viggio-portaria.service | sudo tee /etc/systemd/system/viggio-portaria.service > /dev/null
sed -e "s|__USER__|$INSTALL_USER|g" -e "s|__DIR__|$INSTALL_DIR|g" viggio-kiosk.service | sudo tee /etc/systemd/system/viggio-kiosk.service > /dev/null
sudo systemctl daemon-reload
sudo systemctl enable viggio-portaria viggio-kiosk
sudo systemctl start viggio-portaria

echo "=== Instalação concluída! ==="
echo ""
echo "Próximos passos:"
echo "1. Editar config: nano $INSTALL_DIR/config.json"
echo "2. Adicionar API key do poste ou dispositivo"
echo "3. Reiniciar: sudo reboot"
echo ""
echo "Verificar status: sudo systemctl status viggio-portaria"
