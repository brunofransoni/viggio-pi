#!/usr/bin/env python3
"""
Viggio Tech — Software da Portaria
Polling + controle LED + log de estado
"""

import time
import signal
import sys
import logging
import requests
from config import carregar
from led_controller import LEDController
from audio import tocar, inicializar_sons
from updater import ha_atualizacao, aplicar_atualizacao

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/home/pi/viggio-portaria/viggio.log'),
    ]
)
log = logging.getLogger('viggio')

config = carregar()
led = LEDController(config['canais_portaria'], config['canais_poste'])

estado_anterior = None

def consultar_backend():
    """Consulta o backend e retorna o estado atual das lâmpadas."""
    try:
        resposta = requests.post(
            f"{config['api_url']}/api/postes/heartbeat",
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': config['api_key'],
            },
            json={
                'versaoFirmware': '1.0.0-portaria',
                'conectividade': 'ethernet',
                'ipLocal': 'portaria',
            },
            timeout=8,
        )
        if resposta.ok:
            dados = resposta.json()
            return dados.get('estadoLampada', 'normal')
        log.warning(f'Backend respondeu com status {resposta.status_code}')
        return 'offline'
    except requests.exceptions.ConnectionError:
        log.warning('Sem conexão com o backend')
        return 'offline'
    except Exception as e:
        log.error(f'Erro ao consultar backend: {e}')
        return 'offline'

def processar_estado(estado):
    """Aplica mudanças quando o estado muda."""
    global estado_anterior

    if estado == estado_anterior:
        return  # nada mudou

    log.info(f'Estado mudou: {estado_anterior} → {estado}')
    estado_anterior_local = estado_anterior
    estado_anterior = estado

    led.aplicar_estado(estado)

    # Tocar som conforme urgência
    if estado == 'alerta':
        tocar('alerta', config['volume_alerta'])
        # Tocar 3 vezes para alertas críticos
        time.sleep(0.5)
        tocar('alerta', config['volume_alerta'])
        time.sleep(0.5)
        tocar('alerta', config['volume_alerta'])
    elif estado == 'atencao':
        tocar('atencao', config['volume_alerta'])
    elif estado == 'normal' and estado_anterior_local == 'alerta':
        tocar('ok', config['volume_alerta'])

def verificar_e_atualizar():
    """Se houver uma versão nova no repositório, aplica e reinicia.

    Sai do processo em vez de recarregar módulos em memória — o systemd
    (Restart=always) sobe o processo de novo já com o código atualizado.
    """
    if not ha_atualizacao():
        return
    log.info('Nova versão encontrada, atualizando...')
    if aplicar_atualizacao():
        log.info('Atualização aplicada, reiniciando...')
        sys.exit(0)

def encerrar(sig, frame):
    log.info('Encerrando...')
    led.estado_normal()
    led.desligar()
    sys.exit(0)

signal.signal(signal.SIGTERM, encerrar)
signal.signal(signal.SIGINT, encerrar)

def main():
    log.info('Viggio Tech — Portaria iniciada')
    inicializar_sons()

    if not config['api_key']:
        log.error('API key não configurada! Edite /home/pi/viggio-portaria/config.json')
        led.piscar_alerta('ambos', velocidade=1.0)
        time.sleep(10)

    # Estado inicial
    led.estado_normal()

    proxima_verificacao_update = time.time() + config['update_check_interval']

    while True:
        estado = consultar_backend()
        processar_estado(estado)

        if time.time() >= proxima_verificacao_update:
            verificar_e_atualizar()
            proxima_verificacao_update = time.time() + config['update_check_interval']

        time.sleep(config['polling_interval'])

if __name__ == '__main__':
    main()
