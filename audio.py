import logging
import subprocess
import os
import wave

import numpy as np

log = logging.getLogger('viggio')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SONS_DIR = os.path.join(BASE_DIR, 'sounds')
SONS = {
    'alerta':  os.path.join(SONS_DIR, 'alerta.wav'),
    'atencao': os.path.join(SONS_DIR, 'atencao.wav'),
    'ok':      os.path.join(SONS_DIR, 'ok.wav'),
}

def tocar(tipo, volume=80):
    """Toca um som de alerta de forma não bloqueante.

    Nunca levanta exceção — se o som falhar (ex.: `aplay` ausente, sem
    dispositivo de áudio), isso não pode interromper o resto do
    processamento de estado (LED/sirene) que roda logo em seguida.
    """
    arquivo = SONS.get(tipo)
    if arquivo and os.path.exists(arquivo):
        try:
            subprocess.Popen(
                ['aplay', '-q', arquivo],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except OSError as e:
            log.warning(f'Falha ao tocar som "{tipo}": {e}')

def gerar_beep(arquivo, frequencia=880, duracao=0.5, volume=0.8):
    """Gera um arquivo WAV de beep simples."""
    taxa = 44100
    amostras = int(taxa * duracao)
    t = np.linspace(0, duracao, amostras)
    onda = (np.sin(2 * np.pi * frequencia * t) * volume * 32767).astype(np.int16)

    with wave.open(arquivo, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(taxa)
        f.writeframes(onda.tobytes())

def inicializar_sons():
    """Cria os sons se não existirem."""
    os.makedirs(SONS_DIR, exist_ok=True)
    if not os.path.exists(SONS['alerta']):
        # Beep urgente: alta frequência, curto
        gerar_beep(SONS['alerta'], frequencia=1200, duracao=0.15)
    if not os.path.exists(SONS['atencao']):
        gerar_beep(SONS['atencao'], frequencia=880, duracao=0.3)
    if not os.path.exists(SONS['ok']):
        gerar_beep(SONS['ok'], frequencia=440, duracao=0.2)
