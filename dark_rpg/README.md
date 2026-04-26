# ⚔ Valdrath: The Veil
### A Dark Fantasy Text RPG — Flask + SQLite

---

## 🌑 Lore

Three years ago, King Aldrath III invited an ancient darkness into the Kingdom of Solmere. The Veil consumed the capital Valdrath overnight, corrupting all who touched it. You are one of the **Bound** — warriors marked by the Old Gods, immune to shadow's corruption. You are the last. If the Veil is not sealed, the world follows.

---

## 🚀 Setup

### 1. Clone / unzip the project
```bash
cd dark_rpg
```

### 2. Create a virtual environment (recommended)
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Initialise the database
```bash
python init_db.py
```
This creates `game.db`, seeds all 18 story nodes, and creates 3 test accounts.

### 5. Run the app
```bash
python app.py
```

Visit: **http://localhost:5000**

---

## 🔐 Test Accounts

| Username | Password    | Class   | HP  | ATK |
|----------|-------------|---------|-----|-----|
| fighter  | fighter123  | Fighter | 120 | 18  |
| tank     | tank123     | Tank    | 200 | 10  |
| mage     | mage123     | Mage    | 70  | 30  |

---

## 📁 Project Structure

```
dark_rpg/
├── app.py               # Flask app — routes, auth, combat engine
├── init_db.py           # DB schema + story seeding script
├── game.db              # SQLite database (auto-created)
├── requirements.txt
├── templates/
│   ├── base.html        # Base layout, nav, flash messages
│   ├── login.html       # Login page
│   ├── register.html    # Registration + class selection
│   ├── dashboard.html   # Player sanctum / save overview
│   ├── game.html        # Main game screen (story + combat)
│   └── game_over.html   # Death screen
└── static/
    ├── css/style.css    # Full dark fantasy stylesheet
    └── js/game.js       # Animations + UX enhancements
```

---

## 🗺️ Story Map (18 Nodes)

```
start → crossroads
crossroads
  ├── thornwood_entrance
  │   ├── [COMBAT: Shadow Wolf] → ancient_shrine
  │   └── thornwood_skulk      → ancient_shrine
  │
  └── ashenmere_entrance
      ├── survivor_meeting  → veil_approach
      └── merchant_ruins    → veil_approach

ancient_shrine → veil_approach (+HP or +ATK)

veil_approach
  ├── veil_interior (direct)
  └── reliquary_path
      ├── [COMBAT: Corrupted Guardian] → relic_obtained → veil_interior (+15 ATK)
      └── (back) → veil_approach

veil_interior
  ├── [COMBAT: Shadow Wraith] → throne_approach
  └── veil_detour            → throne_approach

throne_approach
  ├── [COMBAT: Mordechai, Dark Lieutenant] → shadow_throne
  └── throne_appeal → [COMBAT: Mordechai, Shattered Lord] → shadow_throne

shadow_throne
  ├── ending_seal   (seal the Veil — bittersweet)
  └── [COMBAT: Shadow King] → ending_battle (victory)
```

---

## ⚙️ Extending the Game

**Add a story node:** Insert a row in `story_nodes` via `init_db.py` and re-run it.

**Add a stat:** Add the column in `SCHEMA`, update `CLASS_STATS`, and reference it in `app.py`.

**Add a combat ability:** Add a new `action` branch in the `/game/combat` route.

---

## 🎨 Design Notes

- **Fonts:** Cinzel (display / headings) + Crimson Pro (body prose)
- **Palette:** Void black · Parchment text · Gold accents · Blood red combat · Deep purple Veil
- **Animations:** Floating particles, sigil pulse, entity float, HP bar transitions, screen shake on damage, staggered narrative reveal
