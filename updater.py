import subprocess
import logging
import os
import sys

log = logging.getLogger('viggio')

REPO_DIR = os.path.dirname(os.path.abspath(__file__))

def _git(*args, timeout=15):
    return subprocess.run(
        ['git', *args],
        cwd=REPO_DIR,
        check=True,
        timeout=timeout,
        capture_output=True,
        text=True,
    )

def ha_atualizacao():
    """Consulta o remoto e diz se origin/main está à frente do HEAD local."""
    try:
        _git('fetch', '--quiet')
        local = _git('rev-parse', 'HEAD').stdout.strip()
        remoto = _git('rev-parse', '@{u}').stdout.strip()
        return local != remoto
    except Exception as e:
        log.warning(f'Não foi possível verificar atualizações: {e}')
        return False

def _instalar_dependencias():
    """Reinstala requirements.txt na venv em uso (sys.executable já é o
    venv/bin/python, conforme viggio-portaria.service) — sem isso, um commit
    que adiciona uma dependência nova derruba o serviço em loop de restart
    até alguém rodar pip install manualmente."""
    try:
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '-q', '-r', os.path.join(REPO_DIR, 'requirements.txt')],
            check=True, timeout=180, capture_output=True, text=True,
        )
        return True
    except Exception as e:
        log.error(f'Falha ao instalar dependências: {e}')
        return False

def _commit_atual():
    return _git('rev-parse', 'HEAD').stdout.strip()

def _codigo_valido():
    """Confere que os .py do repo pelo menos compilam (pega erro de
    sintaxe/import óbvio) antes de deixar o serviço reiniciar pra essa
    versão. Não executa o código nem toca no hardware/I2C que o processo
    atual já está usando — só valida a sintaxe."""
    try:
        resultado = subprocess.run(
            [sys.executable, '-m', 'compileall', '-q', REPO_DIR],
            timeout=30, capture_output=True, text=True,
        )
        return resultado.returncode == 0
    except Exception as e:
        log.error(f'Erro ao validar código novo: {e}')
        return False

def _reverter_para(commit):
    try:
        _git('reset', '--hard', commit, timeout=15)
        log.warning(f'Revertido pro commit anterior ({commit[:8]}) — segue rodando a versão antiga')
    except Exception as e:
        log.error(f'Falha ao reverter pro commit anterior: {e}')

def aplicar_atualizacao():
    """Faz git pull (fast-forward only), valida e reinstala dependências.

    Se o código novo não compilar ou as dependências novas falharem ao
    instalar, reverte pro commit anterior em vez de deixar o serviço
    reiniciar numa versão quebrada — sem isso, um push ruim no repositório
    travaria TODOS os postes em crash-loop ao mesmo tempo, sem nenhuma forma
    remota de recuperar (o Restart=always só reinicia pro mesmo código
    quebrado). Retorna True se aplicou com sucesso.
    """
    commit_anterior = _commit_atual()

    try:
        _git('pull', '--ff-only', '--quiet', timeout=30)
    except Exception as e:
        log.error(f'Falha ao aplicar atualização: {e}')
        return False

    if not _codigo_valido():
        log.error('Código novo não passou na validação (erro de sintaxe/import)')
        _reverter_para(commit_anterior)
        return False

    if not _instalar_dependencias():
        _reverter_para(commit_anterior)
        return False

    return True
