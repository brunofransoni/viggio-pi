#!/usr/bin/env python3
"""
Viggio Tech — Software da Portaria
Polling + controle LED + log de estado
"""

import os
import socket
import threading
import time
import signal
import sys
import logging
import requests
import socketio
from config import carregar, CONFIG_FILE, BASE_DIR
from led_controller import LEDController
from audio import tocar, inicializar_sons
from updater import ha_atualizacao, aplicar_atualizacao

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(BASE_DIR, 'viggio.log')),
    ]
)
log = logging.getLogger('viggio')

config = carregar()
led = LEDController(
    config['canal_branca'], config['canal_vermelha'], config['canal_amarela'],
    config['canal_buzzer'], config['canal_sirene'], config['rele_ativo_baixo'],
)

estado_anterior = None
sirene_anterior = False
estado_lock = threading.Lock()

# Canal push (Socket.IO) além do polling — reage quase instantaneamente a
# mudanças manuais/alertas, sem esperar o próximo ciclo. O polling continua
# rodando como rede de segurança (heartbeat de online + retorno automático a
# "normal" depois de 60s sem evento, que é baseado em tempo, não em push).
sio = socketio.Client(
    reconnection=True, reconnection_attempts=0,
    reconnection_delay=2, reconnection_delay_max=30,
)

@sio.event
def connect():
    log.info('Socket em tempo real conectado')

@sio.event
def connect_error(dados):
    log.warning(f'Falha ao conectar socket em tempo real: {dados}')

@sio.event
def disconnect():
    log.warning('Socket em tempo real desconectado — seguindo só com polling até reconectar')

@sio.on('poste_estado')
def ao_receber_estado(dados):
    with estado_lock:
        processar_estado(dados.get('estado', 'normal'), dados.get('sirene', False))

def conectar_socket():
    try:
        sio.connect(config['api_url'], auth={'apiKey': config['api_key']}, transports=['websocket'])
    except Exception as e:
        log.warning(f'Socket em tempo real indisponível ({e}) — tenta de novo no próximo ciclo')

def obter_ip_local():
    """Descobre o IP local do Pi na rede (sem depender de serviços externos)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()

def consultar_backend():
    """Consulta o backend e retorna (estadoLampada, sirene)."""
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
                'ipLocal': obter_ip_local(),
            },
            timeout=8,
        )
        if resposta.ok:
            dados = resposta.json()
            return dados.get('estadoLampada', 'normal'), dados.get('sirene', False)
        log.warning(f'Backend respondeu com status {resposta.status_code}')
        return 'offline', False
    except requests.exceptions.ConnectionError:
        log.warning('Sem conexão com o backend')
        return 'offline', False
    except Exception as e:
        log.error(f'Erro ao consultar backend: {e}')
        return 'offline', False

def processar_estado(estado, sirene):
    """Aplica mudanças quando o estado ou a sirene mudam."""
    global estado_anterior, sirene_anterior

    if estado != estado_anterior:
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

    if sirene != sirene_anterior:
        log.info(f'Sirene mudou: {sirene_anterior} → {sirene}')
        sirene_anterior = sirene
        led.definir_sirene(sirene)

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
    if sio.connected:
        sio.disconnect()
    led.desligar()
    sys.exit(0)

signal.signal(signal.SIGTERM, encerrar)
signal.signal(signal.SIGINT, encerrar)

def main():
    log.info('Viggio Tech — Portaria iniciada')
    inicializar_sons()

    if not config['api_key']:
        log.error(f'API key não configurada! Edite {CONFIG_FILE}')
        led.aplicar_estado('alerta')  # vermelho — sinal de erro mais intuitivo
        time.sleep(10)

    # Estado inicial — garante que a sirene comece desligada (o relé fica
    # em estado indefinido até o primeiro comando; sem isso, se o primeiro
    # heartbeat também disser sirene=False, definir_sirene nunca seria
    # chamado por não detectar mudança).
    led.estado_normal()
    led.definir_sirene(False)

    conectar_socket()

    proxima_verificacao_update = time.time() + config['update_check_interval']

    while True:
        estado, sirene = consultar_backend()
        with estado_lock:
            processar_estado(estado, sirene)

        if not sio.connected:
            conectar_socket()

        if time.time() >= proxima_verificacao_update:
            verificar_e_atualizar()
            proxima_verificacao_update = time.time() + config['update_check_interval']

        time.sleep(config['polling_interval'])

if __name__ == '__main__':
    main()
