"""
Testes do updater.py — cobrem principalmente o rollback automático: um
commit que não compila (ou cujas dependências não instalam) tem que reverter
pro commit anterior, não deixar o serviço reiniciar numa versão quebrada.

Uso:
    venv/bin/python -m pytest tests/test_updater.py -v
"""
import os
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import updater  # noqa: E402

COMMIT_ANTERIOR = 'deadbeef1234'


def _run_mock(compileall_returncode=0, pip_deve_falhar=False):
    def _run(cmd, **kwargs):
        if cmd[0] == 'git':
            if cmd[1] == 'rev-parse':
                return MagicMock(stdout=f'{COMMIT_ANTERIOR}\n', returncode=0)
            return MagicMock(stdout='', returncode=0)  # pull / reset
        if 'compileall' in cmd:
            return MagicMock(returncode=compileall_returncode, stdout='', stderr='')
        if 'pip' in cmd:
            if pip_deve_falhar:
                raise subprocess.CalledProcessError(1, cmd)
            return MagicMock(returncode=0)
        raise AssertionError(f'comando inesperado: {cmd}')
    return _run


class TestAplicarAtualizacao(unittest.TestCase):
    def test_sucesso_nao_reverte(self):
        with patch('updater.subprocess.run', side_effect=_run_mock()) as run_mock:
            resultado = updater.aplicar_atualizacao()

        self.assertTrue(resultado)
        chamadas_reset = [c for c in run_mock.call_args_list if c.args[0][:2] == ['git', 'reset']]
        self.assertEqual(chamadas_reset, [])

    def test_codigo_invalido_reverte_pro_commit_anterior(self):
        with patch('updater.subprocess.run', side_effect=_run_mock(compileall_returncode=1)) as run_mock:
            resultado = updater.aplicar_atualizacao()

        self.assertFalse(resultado)
        chamadas_reset = [c for c in run_mock.call_args_list if c.args[0][:2] == ['git', 'reset']]
        self.assertEqual(len(chamadas_reset), 1)
        self.assertEqual(chamadas_reset[0].args[0], ['git', 'reset', '--hard', COMMIT_ANTERIOR])

    def test_falha_ao_instalar_dependencias_reverte_pro_commit_anterior(self):
        with patch('updater.subprocess.run', side_effect=_run_mock(pip_deve_falhar=True)) as run_mock:
            resultado = updater.aplicar_atualizacao()

        self.assertFalse(resultado)
        chamadas_reset = [c for c in run_mock.call_args_list if c.args[0][:2] == ['git', 'reset']]
        self.assertEqual(len(chamadas_reset), 1)
        self.assertEqual(chamadas_reset[0].args[0], ['git', 'reset', '--hard', COMMIT_ANTERIOR])

    def test_falha_no_pull_nao_tenta_reverter(self):
        def _run(cmd, **kwargs):
            if cmd[0] == 'git' and cmd[1] == 'rev-parse':
                return MagicMock(stdout=f'{COMMIT_ANTERIOR}\n', returncode=0)
            if cmd[0] == 'git' and cmd[1] == 'pull':
                raise subprocess.CalledProcessError(1, cmd)
            raise AssertionError(f'comando inesperado: {cmd}')

        with patch('updater.subprocess.run', side_effect=_run) as run_mock:
            resultado = updater.aplicar_atualizacao()

        self.assertFalse(resultado)
        chamadas_reset = [c for c in run_mock.call_args_list if c.args[0][:2] == ['git', 'reset']]
        self.assertEqual(chamadas_reset, [])  # nunca chegou a mudar nada, não tem o que reverter


if __name__ == '__main__':
    unittest.main()
