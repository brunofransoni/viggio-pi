# viggio-portaria

Software que roda no Raspberry Pi 5 do **Poste Sentinela**. Faz polling no
backend Viggio Tech, aciona três lâmpadas (branca/amarela/vermelha), um
buzzer e uma sirene via relés comandados pelo PCA9685, toca sons de alerta e
sobe o Chromium em modo kiosk apontando para o PWA do porteiro.

## Hardware

- Raspberry Pi 5 (lado lógico, 5V DC)
- 2× câmeras USB (CAM1/CAM2)
- PCA9685 via I2C (SDA/SCL/3.3V/GND do Pi)
- 3× módulos relé de 2 canais (SRD-05VDC-SL-C ou equivalente, tipicamente
  **ativo em nível baixo** — sinal LOW energiza o relé), 6 canais ao todo,
  todos usando o contato **NO** (Normalmente Aberto) — o dispositivo só liga
  quando o controlador energiza o relé; em repouso fica tudo desligado. O NC
  de cada relé fica livre:
  - Placa 1, Relé 1 → lâmpada **branca**
  - Placa 1, Relé 2 → lâmpada **vermelha**
  - Placa 2, Relé 1 → lâmpada **amarela**
  - Placa 2, Relé 2 → **buzzer**
  - Placa 3, Relé 1 → **sirene**
  - Placa 3, Relé 2 → livre (expansão futura)

  Esses são os canais PCA9685 de fábrica (`config.example.json`); a ordem
  real de cada instalação pode variar conforme a fiação — use a tela de
  calibração (`calibrar.py`, ver abaixo) pra ajustar sem editar JSON à mão.
- Lado de potência (110/220V AC) isolado do lado lógico: fase passa pelo
  disjuntor até o COM de cada relé; NO alimenta cada lâmpada/buzzer/sirene;
  neutro vai direto às cargas
- Touchscreen HDMI 7" (1024x600)
- Rede cabeada até o backend (Hetzner)

Só o **relé liga/desliga** — não existe mistura de cor como numa fita RGB.
Ver `led_controller.py` para os 4 estados lógicos:

| Estado    | Branca            | Vermelha          | Amarela | Buzzer |
|-----------|-------------------|--------------------|---------|--------|
| `normal`  | fixa ligada       | apagada            | apagada | desligado |
| `atencao` | apagada           | apagada            | fixa ligada | ligado |
| `alerta`  | alternando c/ vermelha (nunca as duas juntas nem as duas apagadas) | alternando c/ branca | apagada | ligado |
| `offline` | apagada           | apagada            | apagada | desligado |

O buzzer segue o estado automaticamente (ligado em `atencao`/`alerta`, só
desliga em `normal`) — sem nada pra configurar no relé além do liga/desliga,
a lógica de tempo é toda em software (o backend volta o estado pra `normal`
sozinho depois de 60s sem novo evento). A sirene é independente do estado:
só liga por comando manual (porteiro/admin), e só enquanto o estado for
`alerta` — o backend força a sirene a desligar assim que o estado muda.

**Importante — isolamento elétrico:** o lado lógico (Pi/PCA9685/relé, 5V) e
o lado de potência (110/220V AC) devem ficar fisicamente isolados; use DPS
(proteção contra surtos) e DR (diferencial residual) no lado de potência.

## Instalação

Clone com o usuário normal que vai rodar o serviço (não root/sudo) — pode
ser qualquer usuário e qualquer diretório, o `install.sh` detecta os dois
automaticamente e usa em tudo (venv, systemd, config):

```bash
git clone https://github.com/brunofransoni/viggio-pi.git viggio-portaria
cd viggio-portaria
bash install.sh
```

O `install.sh` instala dependências do sistema, habilita I2C, cria a venv,
instala os pacotes Python, copia `config.example.json` → `config.json` (se
ainda não existir) e registra os dois serviços systemd (com `User=` e
`WorkingDirectory=` apontando pro usuário/diretório reais do clone).

Depois do install:

```bash
nano config.json   # colar a API key do poste ou dispositivo
sudo reboot
```

## config.json

| Campo               | Descrição                                      |
|---------------------|-------------------------------------------------|
| `api_url`                | URL base do backend Viggio Tech                    |
| `api_key`                | API key do poste ou dispositivo (painel admin)     |
| `polling_interval`       | Intervalo do heartbeat, em segundos                |
| `update_check_interval`  | Intervalo entre checagens de atualização, em segundos |
| `pwa_url`                | URL do PWA aberto no kiosk                         |
| `volume_alerta`          | Volume dos sons de alerta (0-100)                  |
| `canal_branca`           | Canal PCA9685 da lâmpada branca (normal / alterna no alerta) |
| `canal_vermelha`         | Canal PCA9685 da lâmpada vermelha (alterna no alerta)  |
| `canal_amarela`          | Canal PCA9685 da lâmpada amarela (atenção)         |
| `canal_buzzer`           | Canal PCA9685 do buzzer (atenção/alerta)           |
| `canal_sirene`           | Canal PCA9685 da sirene                            |
| `rele_ativo_baixo`       | `true` se os módulos relé acionam em nível lógico baixo (padrão dos SRD-05VDC-SL-C comuns) |

## Atualização automática

`main.py` confere periodicamente (a cada `update_check_interval` segundos,
independente do heartbeat) se `origin/main` avançou. Se sim, faz `git pull
--ff-only` e sai do processo — o systemd (`Restart=always` no
`viggio-portaria.service`) sobe o processo de novo já com o código
atualizado, sem precisar de acesso root para reiniciar o serviço.

Repositório é público (`github.com/brunofransoni/viggio-pi`), então isso
funciona sem nenhum token/credencial configurado no Pi. Se o `git pull`
falhar (ex.: sem internet, ou arquivos alterados manualmente no Pi que
impedem o fast-forward), ele só loga o erro e tenta de novo na próxima
checagem — não derruba o processo em execução.

Pra atualizar manualmente sem esperar o próximo ciclo:
```bash
cd viggio-portaria   # o diretório onde foi clonado
git pull
sudo systemctl restart viggio-portaria
```

## Verificação

```bash
# I2C detecta o PCA9685 no endereço 0x40
i2cdetect -y 1

# Status dos serviços
sudo systemctl status viggio-portaria
sudo systemctl status viggio-kiosk

# Logs em tempo real
journalctl -u viggio-portaria -f
journalctl -u viggio-kiosk -f
```

## Calibração dos canais (instalação)

Cada instalação pode ter os 6 canais em ordem diferente, dependendo de como
o eletricista ligou cada placa de relé. Pra descobrir e já salvar o
mapeamento certo em `config.json`, use a tela de calibração:
```bash
sudo systemctl stop viggio-portaria   # libera o PCA9685
venv/bin/python calibrar.py
```
Acesse `http://<ip-do-pi>:8000` pelo celular/notebook na mesma rede (ou pela
própria touchscreen), clique em "Testar" em cada canal, anote o que acende,
escolha a função (branca/vermelha/amarela/buzzer/sirene/livre) e clique em
"Salvar configuração" — grava direto em `config.json`, sem editar nada à
mão. Depois:
```bash
sudo systemctl start viggio-portaria
```

Se preferir o diagnóstico bruto sem tela (liga um canal por vez, você só
anota o que acendeu):
```bash
sudo systemctl stop viggio-portaria
python3 testar_canais.py
```

## Estrutura

```
viggio-portaria/
├── main.py                  # processo principal (polling + controle LED)
├── led_controller.py        # controle PCA9685 / relés (lâmpadas + buzzer + sirene)
├── calibrar.py              # tela web de calibração dos canais (instalação)
├── testar_canais.py         # diagnóstico bruto de canais (fallback sem tela)
├── audio.py                 # sons de alerta
├── config.py                # loader/saver de config.json
├── config.example.json      # template de config
├── kiosk.sh                 # abre o Chromium em modo kiosk
├── install.sh               # instalação completa no Pi 5
├── viggio-portaria.service  # serviço systemd do processo principal
├── viggio-kiosk.service     # serviço systemd do kiosk
├── tests/                   # testes com PCA9685 simulado
└── requirements.txt
```
