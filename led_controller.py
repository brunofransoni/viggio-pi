import time
import threading
from adafruit_pca9685 import PCA9685
from board import SCL, SDA
import busio

class LEDController:
    """
    Poste Sentinela: 2 lâmpadas (branca/vermelha) acionadas por um relé de
    2 canais, que por sua vez é acionado pelo PCA9685 (OUT0 -> IN1 branca,
    OUT1 -> IN2 vermelha). Um relé é liga/desliga puro — sem mistura de cor
    como numa fita RGB. Módulos SRD-05VDC-SL-C tipicamente são "ativo em
    nível baixo" (sinal LOW energiza a bobina do relé) — ajustável via
    `ativo_baixo` caso o módulo seja o contrário.
    """
    def __init__(self, canal_branca=0, canal_vermelha=1, ativo_baixo=True):
        i2c = busio.I2C(SCL, SDA)
        self.pca = PCA9685(i2c)
        self.pca.frequency = 1000
        self.canal_branca = canal_branca
        self.canal_vermelha = canal_vermelha
        self.ativo_baixo = ativo_baixo
        self._piscando = False
        self._thread_piscar = None

    def _escrever(self, canal, ligado):
        nivel_ligado = 0 if self.ativo_baixo else 65535
        nivel_desligado = 65535 if self.ativo_baixo else 0
        self.pca.channels[canal].duty_cycle = nivel_ligado if ligado else nivel_desligado

    def _definir(self, branca, vermelha):
        self._escrever(self.canal_branca, branca)
        self._escrever(self.canal_vermelha, vermelha)

    def _parar_piscar(self):
        self._piscando = False
        if self._thread_piscar:
            self._thread_piscar.join(timeout=1)

    def _piscar_vermelha(self, velocidade=0.3):
        self._parar_piscar()
        self._piscando = True

        def _loop():
            while self._piscando:
                self._definir(branca=False, vermelha=True)
                time.sleep(velocidade)
                self._definir(branca=False, vermelha=False)
                time.sleep(velocidade)

        self._thread_piscar = threading.Thread(target=_loop, daemon=True)
        self._thread_piscar.start()

    def estado_normal(self):
        """Vermelha acesa (fixa), branca apagada."""
        self._parar_piscar()
        self._definir(branca=False, vermelha=True)

    def aplicar_estado(self, estado):
        """
        Aplica estado vindo do backend.
        estado: 'normal' | 'atencao' | 'alerta' | 'offline'

        normal:  vermelha ligada (fixa)
        atencao: vermelha piscando
        alerta:  branca ligada (fixa)
        offline: tudo apagado
        """
        if estado == 'atencao':
            self._piscar_vermelha(velocidade=0.3)
        elif estado == 'alerta':
            self._parar_piscar()
            self._definir(branca=True, vermelha=False)
        elif estado == 'offline':
            self._parar_piscar()
            self._definir(branca=False, vermelha=False)
        else:
            self.estado_normal()

    def desligar(self):
        self._parar_piscar()
        self._definir(branca=False, vermelha=False)
