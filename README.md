# viggio-portaria

Software que roda no Raspberry Pi 5 do **Poste Sentinela**. Faz polling no
backend Viggio Tech, aciona duas lâmpadas (branca/vermelha) via relé
comandado pelo PCA9685, toca sons de alerta e sobe o Chromium em modo kiosk
apontando para o PWA do porteiro.

## Hardware

- Raspberry Pi 5 (lado lógico, 5V DC)
- PCA9685 via I2C (SDA/SCL/5V/GND do Pi)
- Módulo relé de 2 canais (SRD-05VDC-SL-C ou equivalente, tipicamente
  **ativo em nível baixo** — sinal LOW energiza o relé)
  - PCA9685 OUT0 → relé IN1 → lâmpada **branca**
  - PCA9685 OUT1 → relé IN2 → lâmpada **vermelha**
- Lado de potência (110/220V AC) isolado do lado lógico: fase passa pelo
  disjuntor bipolar até o COM de cada relé; NO1/NO2 alimentam cada grupo de
  lâmpadas; neutro vai direto às lâmpadas
- Touchscreen HDMI 7" (1024x600)
- Rede cabeada até o backend (Hetzner)

Só o **relé liga/desliga** — não existe mistura de cor como numa fita RGB.
Os 4 estados lógicos (`normal`/`atencao`/`alerta`/`offline`) mapeiam pras
combinações fisicamente possíveis de branca/vermelha ligada, desligada ou
piscando — ver `led_controller.py`.

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
| `canal_branca`           | Canal PCA9685 ligado ao IN1 do relé (lâmpada branca) |
| `canal_vermelha`         | Canal PCA9685 ligado ao IN2 do relé (lâmpada vermelha) |
| `rele_ativo_baixo`       | `true` se o módulo relé aciona em nível lógico baixo (padrão dos SRD-05VDC-SL-C comuns) |

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

Estados: `normal` = branca ligada, `atencao` = branca + vermelha ligadas,
`alerta` = vermelha piscando, `offline` = tudo apagado (sem conexão com o
backend).

## Estrutura

```
viggio-portaria/
├── main.py                  # processo principal (polling + controle LED)
├── led_controller.py        # controle PCA9685 / relé (lâmpada branca+vermelha)
├── audio.py                 # sons de alerta
├── config.py                # loader/saver de config.json
├── config.example.json      # template de config
├── kiosk.sh                 # abre o Chromium em modo kiosk
├── install.sh               # instalação completa no Pi 5
├── viggio-portaria.service  # serviço systemd do processo principal
├── viggio-kiosk.service     # serviço systemd do kiosk
└── requirements.txt
```
