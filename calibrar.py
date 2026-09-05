#!/usr/bin/env python3
"""
Tela de calibração dos canais — pra usar na instalação física de cada poste.

Sobe uma página web local (não é um serviço permanente) onde o instalador
liga um canal do PCA9685 por vez, anota visualmente o que acende, atribui a
função (branca/vermelha/amarela/buzzer/sirene/livre) e salva direto em
config.json — substitui o fluxo manual de rodar testar_canais.py e editar o
JSON à mão.

Uso:
    sudo systemctl stop viggio-portaria   # libera o PCA9685
    venv/bin/python calibrar.py
    # abre sozinho no navegador da touchscreen; de outro aparelho na mesma
    # rede, acesse http://<ip-do-pi>:8000
    sudo systemctl start viggio-portaria  # depois de salvar
"""
import threading
import time
import webbrowser

from flask import Flask, request, jsonify, render_template_string
from adafruit_pca9685 import PCA9685
from board import SCL, SDA
import busio

from config import carregar, salvar

NUM_CANAIS = 6
SEGUNDOS_TESTE = 3

FUNCOES = {
    'canal_branca':   'Branca',
    'canal_vermelha': 'Vermelha',
    'canal_amarela':  'Amarela',
    'canal_buzzer':   'Buzzer',
    'canal_sirene':   'Sirene',
    'livre':          'Livre',
}

app = Flask(__name__)

i2c = busio.I2C(SCL, SDA)
pca = PCA9685(i2c)
pca.frequency = 1000

config = carregar()
ativo_baixo = config['rele_ativo_baixo']


def escrever(canal, ligado):
    nivel_ligado = 0 if ativo_baixo else 65535
    nivel_desligado = 65535 if ativo_baixo else 0
    pca.channels[canal].duty_cycle = nivel_ligado if ligado else nivel_desligado


def tudo_desligado():
    for c in range(NUM_CANAIS):
        escrever(c, False)


def mapeamento_atual():
    """canal -> chave de função, a partir do config.json carregado no boot."""
    mapa = {c: 'livre' for c in range(NUM_CANAIS)}
    for chave in FUNCOES:
        if chave == 'livre':
            continue
        canal = config.get(chave)
        if canal is not None and 0 <= canal < NUM_CANAIS:
            mapa[canal] = chave
    return mapa


PAGINA = """
<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Calibração — Poste Sentinela</title>
<style>
  body { font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 1.5rem; }
  h1 { font-size: 1.25rem; margin-bottom: 0.25rem; }
  p.sub { color: #94a3b8; margin-top: 0; margin-bottom: 1.5rem; font-size: 0.9rem; }
  table { width: 100%; border-collapse: collapse; }
  td, th { padding: 0.6rem 0.5rem; border-bottom: 1px solid #334155; text-align: left; }
  select { background: #1e293b; color: #e2e8f0; border: 1px solid #475569; border-radius: 6px; padding: 0.4rem; font-size: 1rem; }
  button { background: #334155; color: #e2e8f0; border: 1px solid #475569; border-radius: 6px; padding: 0.5rem 1rem; font-size: 0.95rem; cursor: pointer; }
  button:hover { background: #475569; }
  button.testando { background: #b45309; border-color: #d97706; }
  #salvar { background: #16a34a; border-color: #15803d; font-weight: 600; margin-top: 1.5rem; padding: 0.7rem 1.4rem; }
  #salvar:hover { background: #15803d; }
  #status { margin-top: 1rem; font-size: 0.9rem; min-height: 1.2rem; }
  #status.ok { color: #4ade80; }
  #status.erro { color: #f87171; }
</style>
</head>
<body>
  <h1>Calibração dos canais — Poste Sentinela</h1>
  <p class="sub">Clique em "Testar" pra ligar aquele canal por {{ segundos }}s, anote o que acendeu, escolha a função e salve no final.</p>
  <table>
    <tr><th>Canal</th><th></th><th>Função</th></tr>
    {% for c in range(num_canais) %}
    <tr>
      <td>Canal {{ c }}</td>
      <td><button type="button" onclick="testar({{ c }}, this)">Testar</button></td>
      <td>
        <select id="funcao-{{ c }}">
          {% for chave, label in funcoes.items() %}
          <option value="{{ chave }}" {{ 'selected' if mapa[c] == chave else '' }}>{{ label }}</option>
          {% endfor %}
        </select>
      </td>
    </tr>
    {% endfor %}
  </table>
  <button id="salvar" onclick="salvarConfig()">Salvar configuração</button>
  <div id="status"></div>

<script>
async function testar(canal, botao) {
  botao.classList.add('testando');
  botao.disabled = true;
  botao.textContent = 'Ligado...';
  try {
    await fetch(`/testar/${canal}`, { method: 'POST' });
  } finally {
    botao.classList.remove('testando');
    botao.disabled = false;
    botao.textContent = 'Testar';
  }
}

async function salvarConfig() {
  const status = document.getElementById('status');
  const mapeamento = {};
  for (let c = 0; c < {{ num_canais }}; c++) {
    mapeamento[c] = document.getElementById(`funcao-${c}`).value;
  }
  const resposta = await fetch('/salvar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mapeamento }),
  });
  const dados = await resposta.json();
  if (resposta.ok) {
    status.className = 'ok';
    status.textContent = 'Salvo em config.json! Pode rodar: sudo systemctl start viggio-portaria';
  } else {
    status.className = 'erro';
    status.textContent = dados.erro || 'Erro ao salvar.';
  }
}
</script>
</body>
</html>
"""


@app.route('/')
def index():
    tudo_desligado()
    return render_template_string(
        PAGINA, num_canais=NUM_CANAIS, funcoes=FUNCOES,
        mapa=mapeamento_atual(), segundos=SEGUNDOS_TESTE,
    )


@app.route('/testar/<int:canal>', methods=['POST'])
def testar(canal):
    if not 0 <= canal < NUM_CANAIS:
        return jsonify(erro='Canal inválido'), 400
    tudo_desligado()
    escrever(canal, True)
    time.sleep(SEGUNDOS_TESTE)
    escrever(canal, False)
    return jsonify(ok=True)


@app.route('/salvar', methods=['POST'])
def salvar_rota():
    mapeamento = request.get_json(force=True).get('mapeamento', {})

    canal_por_funcao = {}
    for canal_str, funcao in mapeamento.items():
        if funcao == 'livre':
            continue
        if funcao in canal_por_funcao:
            return jsonify(erro=f'Duas atribuições para "{FUNCOES[funcao]}" — cada função só pode estar em um canal.'), 400
        canal_por_funcao[funcao] = int(canal_str)

    faltando = [FUNCOES[f] for f in FUNCOES if f != 'livre' and f not in canal_por_funcao]
    if faltando:
        return jsonify(erro=f'Funções sem canal atribuído: {", ".join(faltando)}'), 400

    config_atual = carregar()
    config_atual.update(canal_por_funcao)
    salvar(config_atual)

    global config
    config = config_atual

    return jsonify(ok=True)


def abrir_navegador():
    try:
        webbrowser.open('http://127.0.0.1:8000')
    except Exception:
        pass  # sem navegador local (ex.: rodando via SSH sem display) — segue só pela rede


if __name__ == '__main__':
    threading.Timer(1.0, abrir_navegador).start()
    try:
        app.run(host='0.0.0.0', port=8000)
    finally:
        tudo_desligado()
