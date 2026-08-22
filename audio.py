import subprocess
import os
import wave

import numpy as np

SONS = {
    'alerta':  '/home/pi/viggio-portaria/sounds/alerta.wav',
    'atencao': '/home/pi/viggio-portaria/sounds/atencao.wav',
    'ok':      '/home/pi/viggio-portaria/sounds/ok.wav',
}

def tocar(tipo, volume=80):
    """Toca um som de alerta de forma não bloqueante."""
    arquivo = SONS.get(tipo)
    if arquivo and os.path.exists(arquivo):
        subprocess.Popen(
            ['aplay', '-q', arquivo],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

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
    os.makedirs('/home/pi/viggio-portaria/sounds', exist_ok=True)
    if not os.path.exists(SONS['alerta']):
        # Beep urgente: alta frequência, curto
        gerar_beep(SONS['alerta'], frequencia=1200, duracao=0.15)
    if not os.path.exists(SONS['atencao']):
        gerar_beep(SONS['atencao'], frequencia=880, duracao=0.3)
    if not os.path.exists(SONS['ok']):
        gerar_beep(SONS['ok'], frequencia=440, duracao=0.2)
