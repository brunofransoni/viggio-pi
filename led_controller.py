from adafruit_pca9685 import PCA9685
from board import SCL, SDA
import busio

class LEDController:
    """
    Poste Sentinela: 3 lâmpadas (branca/amarela/vermelha) — uma acesa por
    vez conforme o estado — mais uma sirene controlada separadamente, todas
    via relés de 2 canais acionados pelo PCA9685. Um relé é liga/desliga
    puro — nenhum estado pisca. Módulos SRD-05VDC-SL-C tipicamente são
    "ativo em nível baixo" (sinal LOW energiza a bobina) — ajustável via
    `ativo_baixo` caso o módulo seja o contrário.
    """
    def __init__(self, canal_branca=0, canal_amarela=1, canal_vermelha=2, canal_sirene=3, ativo_baixo=True):
        i2c = busio.I2C(SCL, SDA)
        self.pca = PCA9685(i2c)
        self.pca.frequency = 1000
        self.canal_branca = canal_branca
        self.canal_amarela = canal_amarela
        self.canal_vermelha = canal_vermelha
        self.canal_sirene = canal_sirene
        self.ativo_baixo = ativo_baixo

    def _escrever(self, canal, ligado):
        nivel_ligado = 0 if self.ativo_baixo else 65535
        nivel_desligado = 65535 if self.ativo_baixo else 0
        self.pca.channels[canal].duty_cycle = nivel_ligado if ligado else nivel_desligado

    def estado_normal(self):
        self.aplicar_estado('normal')

    def aplicar_estado(self, estado):
        """
        Aplica estado vindo do backend.
        estado: 'normal' | 'atencao' | 'alerta' | 'offline'

        normal:  branca ligada
        atencao: amarela ligada
        alerta:  vermelha ligada
        offline: todas apagadas
        """
        self._escrever(self.canal_branca, estado == 'normal')
        self._escrever(self.canal_amarela, estado == 'atencao')
        self._escrever(self.canal_vermelha, estado == 'alerta')

    def definir_sirene(self, ligada):
        self._escrever(self.canal_sirene, ligada)

    def desligar(self):
        self.aplicar_estado('offline')
        self.definir_sirene(False)
