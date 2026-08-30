# viggio-portaria

Software que roda no Raspberry Pi 5 instalado na portaria do condomínio. Faz
polling no backend Viggio Tech, controla as fitas LED RGB (portaria + poste)
via PCA9685, toca sons de alerta e sobe o Chromium em modo kiosk apontando
para o PWA do porteiro.

## Hardware

- Raspberry Pi 5 8GB
- Touchscreen HDMI 7" (1024x600)
- PCA9685 via I2C
- Fita LED RGB 5050 12V analógica
  - Canais 0,1,2 → fita da **portaria**
  - Canais 3,4,5 → fio 4 vias → fita do **poste**
- Rede cabeada até o backend (Hetzner)

```
PORTARIA
┌─────────────────────────────────────────────────┐
│                                                 │
│  Raspberry Pi 5                                 │
│  ┌──────────┐                                   │
│  │ GPIO SDA ├──┐                                │
│  │ GPIO SCL ├──┤                                │
│  │ GND      ├──┤                                │
│  │ 3.3V     ├──┘                                │
│  └──────────┘  │                               │
│                ▼                               │
│  ┌─────────────────────┐                       │
│  │     PCA9685          │                       │
│  │  CH0(R) CH1(G) CH2(B)│ → Fita LED portaria  │
│  │  CH3(R) CH4(G) CH5(B)│ → Fio 4 vias → POSTE│
│  │  V+ GND              │ ← Driver 12V          │
│  └─────────────────────┘                       │
│                                                 │
│  Tela HDMI ← Pi 5 (HDMI)                       │
│  Cabo de rede → Hetzner                         │
└─────────────────────────────────────────────────┘
         │
         │ Fio 4 vias (GND + R + G + B), até 50 metros
         ▼
POSTE
┌─────────────────────────────────────────────────┐
│  Fita LED RGB 5050 IP65                         │
│  (alimentada pelo Driver 12V do poste)          │
└─────────────────────────────────────────────────┘
```

## Instalação

```bash
git clone <este repo> /home/pi/viggio-portaria
cd /home/pi/viggio-portaria
bash install.sh
```

O `install.sh` instala dependências do sistema, habilita I2C, cria a venv,
instala os pacotes Python, copia `config.example.json` → `config.json` (se
ainda não existir) e registra os dois serviços systemd.

Depois do install:

```bash
nano /home/pi/viggio-portaria/config.json   # colar a API key do poste
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
| `canais_portaria`        | Canais PCA9685 [R,G,B] da fita da portaria         |
| `canais_poste`           | Canais PCA9685 [R,G,B] da fita do poste            |

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
cd /home/pi/viggio-portaria
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

Estados de LED: `normal` = branco, `atencao` = amarelo, `alerta` = vermelho
piscando, `offline` = azul escuro (sem conexão com o backend).

## Estrutura

```
viggio-portaria/
├── main.py                  # processo principal (polling + controle LED)
├── led_controller.py        # controle PCA9685 / fita RGB
├── audio.py                 # sons de alerta
├── config.py                # loader/saver de config.json
├── config.example.json      # template de config
├── kiosk.sh                 # abre o Chromium em modo kiosk
├── install.sh               # instalação completa no Pi 5
├── viggio-portaria.service  # serviço systemd do processo principal
├── viggio-kiosk.service     # serviço systemd do kiosk
└── requirements.txt
```
