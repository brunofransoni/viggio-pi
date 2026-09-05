#!/usr/bin/env python3
"""
Ferramenta de diagnóstico — liga um canal do PCA9685 por vez (os outros
ficam desligados) pra você anotar visualmente o que cada número de canal
realmente aciona. Não depende do backend nem do main.py.

Uso:
    python3 testar_canais.py

Edite CANAIS_PARA_TESTAR se seu hardware usar mais/menos de 6 canais, ou
ATIVO_BAIXO se `rele_ativo_baixo` no seu config.json for diferente de true.

Pra calibração guiada com tela e gravação automática em config.json, use
calibrar.py — este script aqui é só o diagnóstico bruto de fallback.
"""
import time
from adafruit_pca9685 import PCA9685
from board import SCL, SDA
import busio

CANAIS_PARA_TESTAR = [0, 1, 2, 3, 4, 5]
ATIVO_BAIXO = True
SEGUNDOS_POR_CANAL = 5

i2c = busio.I2C(SCL, SDA)
pca = PCA9685(i2c)
pca.frequency = 1000

nivel_ligado = 0 if ATIVO_BAIXO else 65535
nivel_desligado = 65535 if ATIVO_BAIXO else 0

def tudo_desligado():
    for c in CANAIS_PARA_TESTAR:
        pca.channels[c].duty_cycle = nivel_desligado

print(f"Testando canais {CANAIS_PARA_TESTAR} — {SEGUNDOS_POR_CANAL}s cada, ativo_baixo={ATIVO_BAIXO}")
print("Anote o que acende em cada canal.\n")

tudo_desligado()
time.sleep(1)

try:
    for canal in CANAIS_PARA_TESTAR:
        print(f"--- Canal {canal}: LIGANDO ---")
        pca.channels[canal].duty_cycle = nivel_ligado
        time.sleep(SEGUNDOS_POR_CANAL)
        pca.channels[canal].duty_cycle = nivel_desligado
        print(f"--- Canal {canal}: desligado ---\n")
        time.sleep(1)
finally:
    tudo_desligado()
    print("Teste concluído, tudo desligado.")
