# Beast Intel — YouTube Intelligence Dashboard

A live competitive analytics dashboard tracking MrBeast vs top YouTube competitors. Built for the **Analyst, YouTube Intelligence** role at Beast Industries.

---

## Run Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the server
python app.py

# 3. Open in browser
# http://localhost:5000
```

---

## Deploy to Render (Free)

1. Push this folder to a GitHub repo
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Render auto-detects `render.yaml` — click **Deploy**
5. Your live URL will be: `https://beast-intel-dashboard.onrender.com`

> **Free tier note:** Render free services spin down after 15 min of inactivity. First load after sleep takes ~30 seconds.

---

## What It Shows

| Section | Data |
|---------|------|
| Hero stats | MrBeast subscribers, total views, Social Blade grade, lead vs competitors |
| Channel cards | All 6 channels with stats + clickable |
| Bar charts | Subscriber comparison, avg views per video |
| Benchmark table | Head-to-head across all metrics with inline bar charts |
| Recent videos | Latest uploads across all channels |

---

## Data Sources

- **Social Blade** — subscriber counts, grades, channel stats (public scraping)
- **YouTube oEmbed** — channel thumbnails (free, no API key)
- **Curated fallback** — always-available baseline data so the app never breaks

---

## Project Structure

```
yt_dashboard/
├── app.py            # Flask backend + data fetching
├── templates/
│   └── index.html    # Full dashboard frontend
├── requirements.txt
└── render.yaml       # Render.com deploy config
```
