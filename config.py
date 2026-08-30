import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')

DEFAULTS = {
    'api_url': 'https://api.viggiotech.com.br',
    'api_key': '',           # API key do poste — obtida no painel admin
    'polling_interval': 5,  # segundos
    'update_check_interval': 1800,  # segundos entre checagens de atualização (30 min)
    'pwa_url': 'https://app.viggiotech.com.br',
    'volume_alerta': 80,     # 0-100
    # Canais PCA9685
    'canais_portaria': [0, 1, 2],  # R, G, B da portaria
    'canais_poste':    [3, 4, 5],  # R, G, B do poste
}

def carregar():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            dados = json.load(f)
            return {**DEFAULTS, **dados}
    return DEFAULTS.copy()

def salvar(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
