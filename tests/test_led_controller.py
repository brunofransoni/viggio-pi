"""
Teste funcional do LEDController contra um PCA9685 simulado (sem hardware
real) — injeta módulos falsos em sys.modules antes de importar
led_controller, já que adafruit_pca9685/board/busio só existem na venv do Pi.

Uso:
    venv/bin/python -m pytest tests/test_led_controller.py -v
"""
import os
import sys
import time
import types
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _instalar_stubs_hardware():
    canais_fake = [MagicMock(duty_cycle=None) for _ in range(16)]

    pca_instancia = MagicMock()
    pca_instancia.channels = canais_fake

    modulo_pca9685 = types.ModuleType('adafruit_pca9685')
    modulo_pca9685.PCA9685 = MagicMock(return_value=pca_instancia)
    sys.modules['adafruit_pca9685'] = modulo_pca9685

    modulo_board = types.ModuleType('board')
    modulo_board.SCL = 'SCL'
    modulo_board.SDA = 'SDA'
    sys.modules['board'] = modulo_board

    modulo_busio = types.ModuleType('busio')
    modulo_busio.I2C = MagicMock(return_value=MagicMock())
    sys.modules['busio'] = modulo_busio

    return canais_fake


CANAIS_FAKE = _instalar_stubs_hardware()

from led_controller import LEDController  # noqa: E402


def _ligado(canal):
    return CANAIS_FAKE[canal].duty_cycle == 0  # ativo_baixo=True nos testes


class TestLEDController(unittest.TestCase):
    def setUp(self):
        for c in CANAIS_FAKE:
            c.duty_cycle = None
        self.led = LEDController(
            canal_branca=0, canal_vermelha=1, canal_amarela=2,
            canal_buzzer=3, canal_sirene=4, ativo_baixo=True,
        )

    def tearDown(self):
        self.led._parar_thread_alternancia()

    def test_normal_acende_so_branca_sem_buzzer(self):
        self.led.aplicar_estado('normal')
        self.assertTrue(_ligado(0))
        self.assertFalse(_ligado(1))
        self.assertFalse(_ligado(2))
        self.assertFalse(_ligado(3))

    def test_atencao_acende_so_amarela_com_buzzer(self):
        self.led.aplicar_estado('atencao')
        self.assertFalse(_ligado(0))
        self.assertFalse(_ligado(1))
        self.assertTrue(_ligado(2))
        self.assertTrue(_ligado(3))

    def test_offline_apaga_tudo_incluindo_buzzer(self):
        self.led.aplicar_estado('atencao')
        self.led.aplicar_estado('offline')
        self.assertFalse(_ligado(0))
        self.assertFalse(_ligado(1))
        self.assertFalse(_ligado(2))
        self.assertFalse(_ligado(3))

    def test_alerta_alterna_branca_vermelha_com_buzzer_ligado(self):
        self.led.aplicar_estado('alerta')
        self.assertFalse(_ligado(2))  # amarela sempre apagada
        self.assertTrue(_ligado(3))   # buzzer ligado

        estados_observados = set()
        for _ in range(6):
            branca, vermelha = _ligado(0), _ligado(1)
            # nunca as duas ligadas nem as duas apagadas ao mesmo tempo
            self.assertNotEqual(branca, vermelha)
            estados_observados.add(branca)
            time.sleep(0.15)

        # ao longo de várias leituras, a alternância realmente aconteceu
        self.assertEqual(estados_observados, {True, False})

    def test_sair_do_alerta_para_a_alternancia(self):
        self.led.aplicar_estado('alerta')
        time.sleep(0.1)
        thread_antiga = self.led._thread_alternancia
        self.led.aplicar_estado('normal')
        self.assertIsNone(self.led._thread_alternancia)
        self.assertFalse(thread_antiga.is_alive())

    def test_sirene_independente_do_estado(self):
        self.led.aplicar_estado('normal')
        self.led.definir_sirene(True)
        self.assertTrue(_ligado(4))
        self.led.aplicar_estado('atencao')
        self.assertTrue(_ligado(4))  # não é afetada por aplicar_estado
        self.led.definir_sirene(False)
        self.assertFalse(_ligado(4))

    def test_desligar_para_alternancia_e_apaga_sirene(self):
        self.led.aplicar_estado('alerta')
        self.led.definir_sirene(True)
        self.led.desligar()
        self.assertIsNone(self.led._thread_alternancia)
        self.assertFalse(_ligado(0))
        self.assertFalse(_ligado(1))
        self.assertFalse(_ligado(3))
        self.assertFalse(_ligado(4))


if __name__ == '__main__':
    unittest.main()
