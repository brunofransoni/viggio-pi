# viggio-portaria

Software que roda no Raspberry Pi 5 do **Poste Sentinela**. Faz polling no
backend Viggio Tech, aciona três lâmpadas (branca/amarela/vermelha) e uma
sirene via relés comandados pelo PCA9685, toca sons de alerta e sobe o
Chromium em modo kiosk apontando para o PWA do porteiro.

## Hardware

- Raspberry Pi 5 (lado lógico, 5V DC)
- 2× câmeras USB (CAM1/CAM2)
- PCA9685 via I2C (SDA/SCL/3.3V/GND do Pi)
- 2× módulos relé de 2 canais (SRD-05VDC-SL-C ou equivalente, tipicamente
  **ativo em nível baixo** — sinal LOW energiza o relé) — 4 canais ao todo:
  - PCA9685 PWM0 → lâmpada **branca**
  - PCA9685 PWM1 → lâmpada **amarela**
  - PCA9685 PWM2 → lâmpada **vermelha**
  - PCA9685 PWM3 → **sirene**
- Lado de potência (110/220V AC) isolado do lado lógico: fase passa pelo
  disjuntor até o COM de cada relé; NO alimenta cada lâmpada/sirene; neutro
  vai direto às cargas
- Touchscreen HDMI 7" (1024x600)
- Rede cabeada até o backend (Hetzner)

Só o **relé liga/desliga** — não existe mistura de cor como numa fita RGB, e
nenhum estado pisca. Cada um dos 4 estados lógicos (`normal`/`atencao`/
`alerta`/`offline`) acende exatamente uma lâmpada fixa (ou nenhuma, no caso
de `offline`) — ver `led_controller.py`. A sirene é independente do estado:
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
| `canal_branca`           | Canal PCA9685 da lâmpada branca (normal)           |
| `canal_amarela`          | Canal PCA9685 da lâmpada amarela (atenção)         |
| `canal_vermelha`         | Canal PCA9685 da lâmpada vermelha (alerta)         |
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

Estados: `normal` = branca ligada, `atencao` = amarela ligada, `alerta` =
vermelha ligada, `offline` = tudo apagado (sem conexão com o backend) —
nenhum pisca. Sirene liga/desliga por comando manual, só válido durante
`alerta`.

## Estrutura

```
viggio-portaria/
├── main.py                  # processo principal (polling + controle LED)
├── led_controller.py        # controle PCA9685 / relés (lâmpadas + sirene)
├── audio.py                 # sons de alerta
├── config.py                # loader/saver de config.json
├── config.example.json      # template de config
├── kiosk.sh                 # abre o Chromium em modo kiosk
├── install.sh               # instalação completa no Pi 5
├── viggio-portaria.service  # serviço systemd do processo principal
├── viggio-kiosk.service     # serviço systemd do kiosk
└── requirements.txt
```
