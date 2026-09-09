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

def aplicar_atualizacao():
    """Faz git pull (fast-forward only) e reinstala dependências. Retorna True se aplicou com sucesso."""
    try:
        _git('pull', '--ff-only', '--quiet', timeout=30)
    except Exception as e:
        log.error(f'Falha ao aplicar atualização: {e}')
        return False

    return _instalar_dependencias()
