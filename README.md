# BORIS Telegram Bot

Минимальный Telegram bot layer. `core/` живет отдельно на сервере и не входит в репозиторий.

## Deploy

На сервере нужно перейти в директорию проекта, а не запускать ее как команду:

```bash
cd /opt/boris-telegram-bot
git pull
```

Если виртуальное окружение еще не создано:

```bash
apt update
apt install -y python3.12-venv
python3 -m venv venv
```

Установка зависимостей должна идти через venv:

```bash
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
sudo systemctl restart boris-telegram-bot
```

Проверка логов:

```bash
sudo journalctl -u boris-telegram-bot -n 100 --no-pager
```
