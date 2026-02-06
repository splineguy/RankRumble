# RankRumble

**Battle it out. Crown the best.**

RankRumble is a web app that lets you rank anything using the ELO rating system. Compare items head-to-head, watch ratings evolve over time, and run Sweet Sixteen double-elimination tournaments to crown a champion.

## Features

- **ELO Battle Arena** — Compare two items side-by-side. Pick your favorite and watch ratings update in real time. Multiple matchup strategies: random, least compared, or similar ratings.
- **Sweet Sixteen Tournament** — Select 16 items for a full double-elimination bracket. Winners bracket, losers bracket, grand final, and a reset match if the underdog wins. Every match updates ELO ratings. Confetti when a champion is crowned.
- **Rankings & Charts** — Full sortable rankings with Chart.js visualizations. Track win rates, battle history, and rating progression over time for every item.
- **Multi-Project Support** — Create unlimited ranking projects: movies, restaurants, albums, games — anything you want to compare.
- **Import & Export** — Bulk import items from TXT, CSV, or JSON files. Export rankings as CSV or JSON.
- **User Accounts** — Multi-user support with secure authentication. Each user has their own projects and data.

## Tech Stack

- **Backend:** Flask, Flask-Login, Flask-WTF, Bcrypt
- **Frontend:** Jinja2 templates, Tailwind CSS, vanilla JavaScript, Chart.js
- **Storage:** JSON file-based with thread-safe file locking
- **Server:** Gunicorn (production), Flask dev server (development)

## Quick Start

```bash
# Clone the repo
git clone https://github.com/splineguy/ELO_Sorting.git
cd ELO_Sorting

# Create a virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your secret key

# Run the app
python run.py
```

The app will be available at **http://localhost:5001**.

## Project Structure

```
app/
├── __init__.py              # App factory
├── config.py                # Configuration
├── core/
│   └── elo.py               # ELO rating algorithm
├── models/
│   ├── user.py              # User management
│   ├── project.py           # Project & battle management
│   ├── tournament.py        # Double-elimination tournaments
│   └── storage.py           # Thread-safe JSON storage
├── blueprints/
│   ├── auth/                # Login, register, logout
│   ├── projects/            # Project CRUD, items, import/export
│   ├── battles/             # Battle arena & history
│   ├── tournament/          # Tournament setup, bracket, play
│   └── api/                 # REST API for AJAX operations
├── templates/               # Jinja2 HTML templates
└── static/                  # CSS and assets
```

## How ELO Works

Each item starts with a default rating (1000). When two items battle:

1. **Expected scores** are calculated based on current ratings
2. The winner's rating goes up, the loser's goes down
3. Upsets (lower-rated beating higher-rated) cause bigger swings
4. The **K-factor** controls how much ratings change per battle (configurable per project)

## Sweet Sixteen Tournament

The tournament uses a standard 16-seed double-elimination format:

- **Winners Bracket:** 4 rounds (8 → 4 → 2 → 1 matches)
- **Losers Bracket:** 6 rounds — lose once and you drop here; lose twice and you're out
- **Grand Final:** Winners bracket champion vs losers bracket champion
- **Reset Match:** If the losers bracket champion wins the grand final, one final "true final" decides it all
- **30-31 total matches** per tournament, each affecting ELO ratings

Items are seeded by current ELO rating (1 vs 16, 8 vs 9, etc.).

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/projects/<id>/pair` | Get battle matchup |
| POST | `/api/v1/projects/<id>/battle` | Submit battle result |
| GET | `/api/v1/projects/<id>/rankings` | Get rankings |
| GET | `/api/v1/projects/<id>/items` | List all items |
| GET | `/api/v1/projects/<id>/stats` | Project statistics |
| GET | `/api/v1/projects/<id>/history` | Battle history |
| POST | `/api/v1/projects/<id>/tournaments` | Create tournament |
| GET | `/api/v1/projects/<id>/tournaments/<tid>/next-match` | Get next tournament match |
| POST | `/api/v1/projects/<id>/tournaments/<tid>/match` | Submit tournament match |

## License

This project is licensed under the [MIT License](LICENSE).
