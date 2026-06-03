# Arabic Tech News Bot 🤖📰

A production-ready Telegram bot that posts **one short Arabic technology-news
summary** to your channel **every day at 09:00 Uzbekistan time
(`Asia/Tashkent`)**.

Each post is written in **Modern Standard Arabic with full harakat/tashkīl**,
sized for **A2–B1 learners** (50–70 Arabic words), and formatted like this:

```
📰 العُنْوَانُ:
تَطْبِيقٌ جَدِيدٌ لِتَعَلُّمِ اللُّغَاتِ

أَطْلَقَتْ شَرِكَةٌ تِقْنِيَّةٌ تَطْبِيقًا جَدِيدًا يُسَاعِدُ الطُّلَّابَ عَلَى تَعَلُّمِ اللُّغَاتِ ...

🔗 المَصْدَرُ: https://example.com
```

## Features

- Fetches the latest tech news from configurable RSS feeds.
- Skips duplicates by URL (SQLite-backed).
- Summarizes in Arabic with full harakat via OpenAI.
- Validates AI output — **broken or empty content is never sent**.
- If one source fails, the others keep working.
- Daily scheduling with APScheduler in `Asia/Tashkent`.
- Admin-only commands: `/start`, `/send_now`, `/latest`, `/status`, `/sources`.
- Docker & docker-compose support for easy VPS deployment.

## Project structure

```
arabic-tech-news-bot/
├── bot.py               # Entry point, Telegram handlers, lifecycle
├── config.yaml          # Schedule, sources, post settings
├── requirements.txt
├── .env.example
├── README.md
├── database.py          # SQLite: sent_news + generated_posts
├── news_fetcher.py      # RSS fetching & fresh-item selection
├── ai_generator.py      # OpenAI Arabic generation + validation
├── scheduler.py         # APScheduler daily job (Asia/Tashkent)
├── utils.py             # Config/env loading, logging, helpers
├── Dockerfile
├── docker-compose.yml
└── tests/
    ├── test_news_fetcher.py
    └── test_ai_generator.py
```

---

## Setup guide

### 1. Create a bot with BotFather

1. Open Telegram and search for [`@BotFather`](https://t.me/BotFather).
2. Send `/newbot`.
3. Choose a **name** (e.g. `Arabic Tech News`) and a **username** ending in
   `bot` (e.g. `arabic_tech_news_bot`).

### 2. Get the bot token

BotFather replies with a token like:

```
123456789:AAFooBarBazQuxQuux-Token-Here
```

Copy it — this is your `BOT_TOKEN`. **Keep it secret.** If it ever leaks, send
`/revoke` to BotFather to generate a new one.

### 3. Add the bot to your channel as admin

1. Open your channel → **Manage Channel → Administrators → Add Admin**.
2. Search for your bot's username and add it.
3. Give it at least the **Post Messages** permission.

### 4. Get the channel ID / use @channel_username

- **Public channel:** just use its username, e.g. `@my_tech_channel`.
- **Private channel:** use the numeric ID (looks like `-1001234567890`).
  To find it: temporarily make the channel public to read the username, or
  forward a channel message to [`@userinfobot`](https://t.me/userinfobot) /
  [`@getidsbot`](https://t.me/getidsbot), or check
  `https://api.telegram.org/bot<TOKEN>/getUpdates` after posting in the channel.

### 5. Get your admin user ID

Message [`@userinfobot`](https://t.me/userinfobot) — it replies with your
numeric Telegram user ID. Put it in `ADMIN_IDS` (comma-separated for multiple
admins).

### 6. Fill `.env`

Copy the example and edit it:

```bash
cp .env.example .env
```

```dotenv
BOT_TOKEN=123456789:AAFooBarBazQux-Token-Here
CHANNEL_ID=@your_channel_username_or_-100xxxxxxxxxx
ADMIN_IDS=123456789,987654321
OPENAI_API_KEY=sk-...
TIMEZONE=Asia/Tashkent
```

> `.env` is git-ignored. **Never commit real secrets.**

### 7. Install requirements

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 8. Run locally

```bash
python bot.py
```

You should see log lines confirming the scheduler started. Open a private chat
with your bot and send `/start`.

### 9. Run on a VPS

Recommended: a simple `systemd` service.

```ini
# /etc/systemd/system/arabic-news-bot.service
[Unit]
Description=Arabic Tech News Bot
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=/opt/arabic-tech-news-bot
ExecStart=/opt/arabic-tech-news-bot/.venv/bin/python bot.py
Restart=always
RestartSec=5
EnvironmentFile=/opt/arabic-tech-news-bot/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now arabic-news-bot
sudo journalctl -u arabic-news-bot -f
```

### 10. Run with Docker

```bash
cp .env.example .env   # then edit .env
docker compose up -d --build
docker compose logs -f
```

The SQLite database is persisted in `./data` and `config.yaml` is mounted
read-only.

---

## Test `/send_now`

1. Start the bot (locally, VPS, or Docker).
2. In a **private chat with the bot** (as an admin), send `/send_now`.
3. The bot fetches fresh news, generates the Arabic post, and **sends it to the
   channel immediately**. It replies `✅ Sent to the channel.` on success.
4. Use `/latest` to preview without sending, and `/status` to see last/next run.

---

## Admin commands

| Command      | Description                                              |
|--------------|----------------------------------------------------------|
| `/start`     | Show bot status and next scheduled run.                  |
| `/send_now`  | Generate and **send** one post to the channel now.       |
| `/latest`    | Generate and **preview** the latest post (not sent).     |
| `/status`    | Show last sent time, next scheduled time, DB counts.     |
| `/sources`   | List configured news sources.                            |

Only user IDs listed in `ADMIN_IDS` can use these commands.

---

## Configuration (`config.yaml`)

```yaml
schedule:
  hour: 9
  minute: 0
  timezone: "Asia/Tashkent"

news:
  max_items_to_check: 10
  sources:
    - name: "TechCrunch"
      url: "https://techcrunch.com/feed/"
    - name: "The Verge"
      url: "https://www.theverge.com/rss/index.xml"
    - name: "MIT Technology Review"
      url: "https://www.technologyreview.com/feed/"

post:
  language: "Arabic"
  min_words: 50
  max_words: 70
  add_harakat: true
  level: "A2-B1"
```

Change the time, timezone, or add/remove RSS sources here — no code changes
needed.

---

## Running tests

```bash
pip install pytest
pytest -v
```

Tests mock all network and OpenAI calls, so they run offline.

---

## Notes & safety

- Content moderation is enforced via the system prompt (no politics, religion,
  adult content, violence).
- The bot validates word count and required format markers before sending.
- Duplicate news is prevented by storing every sent URL in `sent_news`.
