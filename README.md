# RootHelper

Helper para grupos de ROMs (Bot API — não é userbot).

## Comandos
- `/start` `/rules` `/setrules` (admin) — regras
- `/report` (responder msg) — marca admins
- `/note` `/delnote` `!gatilho` — notas do grupo
- `/warn` `/unwarn` — 3 warns = mute
- `/pin` (responder msg)
- Antiflood automático (6 msgs/10s), welcome

## Rodar
```bash
cp bot.env.sample bot.env   # preencha BOT_TOKEN (@BotFather) e OWNER_ID
python -m venv .venv && .venv/bin/pip install -r requirements.txt
BOT_TOKEN=... OWNER_ID=... .venv/bin/python bot.py
```

## VPS (systemd)
```bash
sudo cp roothelper.service /etc/systemd/system/
sudo systemctl enable --now roothelper
```

## Docker
```bash
docker build -t roothelper .
docker run -d --restart unless-stopped --env-file bot.env roothelper
```
