import threading
import time

from adafruit_pca9685 import PCA9685
from board import SCL, SDA
import busio

INTERVALO_ALTERNANCIA = 0.5  # segundos entre branca/vermelha durante o alerta

class LEDController:
    """
    Poste Sentinela: 3 placas de relé de 2 canais (6 canais no total, contato
    NO) — branca, vermelha, amarela, buzzer e sirene, mais um canal livre
    para expansão futura. Módulos SRD-05VDC-SL-C tipicamente são "ativo em
    nível baixo" (sinal LOW energiza a bobina) — ajustável via `ativo_baixo`
    caso o módulo seja o contrário.
    """
    def __init__(self, canal_branca=0, canal_vermelha=1, canal_amarela=2, canal_buzzer=3, canal_sirene=4, ativo_baixo=True):
        i2c = busio.I2C(SCL, SDA)
        self.pca = PCA9685(i2c)
        self.pca.frequency = 1000
        self.canal_branca = canal_branca
        self.canal_vermelha = canal_vermelha
        self.canal_amarela = canal_amarela
        self.canal_buzzer = canal_buzzer
        self.canal_sirene = canal_sirene
        self.ativo_baixo = ativo_baixo
        self._thread_alternancia = None
        self._parar_alternancia = threading.Event()

    def _escrever(self, canal, ligado):
        nivel_ligado = 0 if self.ativo_baixo else 65535
        nivel_desligado = 65535 if self.ativo_baixo else 0
        self.pca.channels[canal].duty_cycle = nivel_ligado if ligado else nivel_desligado

    def _parar_thread_alternancia(self):
        if self._thread_alternancia is not None:
            self._parar_alternancia.set()
            self._thread_alternancia.join()
            self._thread_alternancia = None

    def _loop_alternancia(self):
        branca_ligada = True
        while not self._parar_alternancia.is_set():
            self._escrever(self.canal_branca, branca_ligada)
            self._escrever(self.canal_vermelha, not branca_ligada)
            branca_ligada = not branca_ligada
            self._parar_alternancia.wait(INTERVALO_ALTERNANCIA)

    def estado_normal(self):
        self.aplicar_estado('normal')

    def aplicar_estado(self, estado):
        """
        Aplica estado vindo do backend.
        estado: 'normal' | 'atencao' | 'alerta' | 'offline'

        normal:  branca fixa ligada, buzzer desligado
        atencao: amarela fixa ligada, buzzer ligado
        alerta:  branca e vermelha alternando continuamente, buzzer ligado
        offline: tudo apagado
        """
        self._parar_thread_alternancia()

        if estado == 'alerta':
            self._escrever(self.canal_amarela, False)
            self._parar_alternancia.clear()
            self._thread_alternancia = threading.Thread(target=self._loop_alternancia, daemon=True)
            self._thread_alternancia.start()
        else:
            self._escrever(self.canal_branca, estado == 'normal')
            self._escrever(self.canal_vermelha, False)
            self._escrever(self.canal_amarela, estado == 'atencao')

        self._escrever(self.canal_buzzer, estado in ('atencao', 'alerta'))

    def definir_sirene(self, ligada):
        self._escrever(self.canal_sirene, ligada)

    def desligar(self):
        self.aplicar_estado('offline')
        self.definir_sirene(False)
