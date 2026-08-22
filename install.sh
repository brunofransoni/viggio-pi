#!/bin/bash
# Viggio Tech — Instalação completa no Raspberry Pi 5
# Rodar como: bash install.sh

set -e
echo "=== Viggio Tech — Instalação da Portaria ==="

# 1. Atualizar sistema
sudo apt-get update && sudo apt-get upgrade -y

# 2. Instalar dependências do sistema
sudo apt-get install -y \
  python3 python3-pip python3-venv \
  chromium-browser \
  unclutter \
  alsa-utils \
  i2c-tools \
  libgpiod2

# 3. Habilitar I2C no Pi 5
sudo raspi-config nonint do_i2c 0
echo "I2C habilitado"

# 4. Criar ambiente virtual Python
python3 -m venv /home/pi/viggio-portaria/venv
source /home/pi/viggio-portaria/venv/bin/activate

# 5. Instalar dependências Python
pip install -r requirements.txt

# 6. Criar config inicial a partir do template
if [ ! -f /home/pi/viggio-portaria/config.json ]; then
  cp config.example.json /home/pi/viggio-portaria/config.json
  echo "⚠️  Edite /home/pi/viggio-portaria/config.json e adicione a API key!"
fi

# 7. Permissão de execução
chmod +x kiosk.sh

# 8. Instalar serviços systemd
sudo cp viggio-portaria.service /etc/systemd/system/
sudo cp viggio-kiosk.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable viggio-portaria viggio-kiosk
sudo systemctl start viggio-portaria

echo "=== Instalação concluída! ==="
echo ""
echo "Próximos passos:"
echo "1. Editar config: nano /home/pi/viggio-portaria/config.json"
echo "2. Adicionar API key do poste"
echo "3. Reiniciar: sudo reboot"
echo ""
echo "Verificar status: sudo systemctl status viggio-portaria"
