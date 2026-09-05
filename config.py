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
    # PCA9685 -> 3 placas de relé de 2 canais -> branca/vermelha/amarela/buzzer/sirene
    'canal_branca':    0,
    'canal_vermelha':  1,
    'canal_amarela':   2,
    'canal_buzzer':    3,
    'canal_sirene':    4,
    'rele_ativo_baixo': True,  # SRD-05VDC-SL-C tipicamente aciona em nível baixo
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
