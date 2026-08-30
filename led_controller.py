import time
import threading
from adafruit_pca9685 import PCA9685
from board import SCL, SDA
import busio

# Cores predefinidas (valores 0-65535 para 16-bit PWM)
# Fita RGB analógica: 0 = apagado, 65535 = máximo brilho
CORES = {
    'normal':   (45000, 38000, 22000),  # branco quente suave
    'atencao':  (65535, 45000, 0    ),  # amarelo
    'alerta':   (65535, 0,     0    ),  # vermelho
    'offline':  (0,     0,     16383),  # azul escuro
    'apagado':  (0,     0,     0    ),  # apagado
}

class LEDController:
    def __init__(self, canais_portaria, canais_poste):
        i2c = busio.I2C(SCL, SDA)
        self.pca = PCA9685(i2c)
        self.pca.frequency = 1000  # 1kHz para LEDs
        self.canais_portaria = canais_portaria
        self.canais_poste = canais_poste
        self._piscando = False
        self._thread_piscar = None

    def _set_rgb(self, canais, r, g, b):
        """Define cor diretamente nos canais do PCA9685."""
        self.pca.channels[canais[0]].duty_cycle = r
        self.pca.channels[canais[1]].duty_cycle = g
        self.pca.channels[canais[2]].duty_cycle = b

    def set_cor(self, local, estado):
        """Define cor de um local (portaria ou poste) para um estado."""
        r, g, b = CORES.get(estado, CORES['normal'])
        canais = self.canais_portaria if local == 'portaria' else self.canais_poste
        self._set_rgb(canais, r, g, b)

    def piscar_alerta(self, local='ambos', velocidade=0.4):
        """Faz os LEDs piscarem em vermelho — para alertas críticos."""
        self._parar_piscar()
        self._piscando = True

        def _loop():
            while self._piscando:
                if local in ('portaria', 'ambos'):
                    self._set_rgb(self.canais_portaria, *CORES['alerta'])
                if local in ('poste', 'ambos'):
                    self._set_rgb(self.canais_poste, *CORES['alerta'])
                time.sleep(velocidade)

                if local in ('portaria', 'ambos'):
                    self._set_rgb(self.canais_portaria, *CORES['apagado'])
                if local in ('poste', 'ambos'):
                    self._set_rgb(self.canais_poste, *CORES['apagado'])
                time.sleep(velocidade)

        self._thread_piscar = threading.Thread(target=_loop, daemon=True)
        self._thread_piscar.start()

    def _parar_piscar(self):
        self._piscando = False
        if self._thread_piscar:
            self._thread_piscar.join(timeout=1)

    def estado_normal(self):
        """Volta tudo para estado normal."""
        self._parar_piscar()
        self.set_cor('portaria', 'normal')
        self.set_cor('poste', 'normal')

    def aplicar_estado(self, estado):
        """
        Aplica estado vindo do backend.
        estado: 'normal' | 'atencao' | 'alerta' | 'offline'
        """
        if estado == 'alerta':
            self.piscar_alerta('ambos', velocidade=0.3)
        elif estado == 'atencao':
            self._parar_piscar()
            self.set_cor('portaria', 'atencao')
            self.set_cor('poste', 'atencao')
        elif estado == 'offline':
            self._parar_piscar()
            self.set_cor('portaria', 'offline')
            self.set_cor('poste', 'offline')
        else:
            self.estado_normal()

    def desligar(self):
        self._parar_piscar()
        for i in range(16):
            self.pca.channels[i].duty_cycle = 0
