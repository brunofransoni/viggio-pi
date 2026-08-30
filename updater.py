import subprocess
import logging
import os

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

def aplicar_atualizacao():
    """Faz git pull (fast-forward only). Retorna True se aplicou com sucesso."""
    try:
        _git('pull', '--ff-only', '--quiet', timeout=30)
        return True
    except Exception as e:
        log.error(f'Falha ao aplicar atualização: {e}')
        return False
