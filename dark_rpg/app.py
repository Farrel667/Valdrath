"""
Dark Fantasy Text RPG — Valdrath: The Veil
Flask backend: story engine, auth, turn-based combat with class skills & cooldowns.
"""

import os
import json
import random
from functools import wraps

from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

# ──────────────────────────────────────────────────────────────────────────────
# App Setup
# ──────────────────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "veil-shrouds-all-secrets-2024")
DATABASE = "game.db"


# ──────────────────────────────────────────────────────────────────────────────
# Database Helpers
# ──────────────────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def get_user(user_id: int) -> dict | None:
    db  = get_db()
    row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    db.close()
    return dict(row) if row else None


def get_node(node_id: str) -> dict | None:
    db  = get_db()
    row = db.execute("SELECT * FROM story_nodes WHERE node_id = ?", (node_id,)).fetchone()
    db.close()
    if not row:
        return None
    node = dict(row)
    node["choices"] = json.loads(node["choices"]) if node["choices"] else []
    return node


def update_user(user_id: int, **kwargs):
    db     = get_db()
    clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [user_id]
    db.execute(f"UPDATE users SET {clause} WHERE id = ?", values)
    db.commit()
    db.close()


# ──────────────────────────────────────────────────────────────────────────────
# Auth Decorator
# ──────────────────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("You must be logged in to continue.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ──────────────────────────────────────────────────────────────────────────────
# Class Configuration
# ──────────────────────────────────────────────────────────────────────────────

CLASS_STATS = {
    "fighter": {
        "hp": 120, "max_hp": 120, "attack": 18,
        "description": "Balanced warrior. High resilience, reliable damage.",
        "icon": "⚔️"
    },
    "tank": {
        "hp": 200, "max_hp": 200, "attack": 10,
        "description": "Ironclad guardian. Immense endurance, low burst damage.",
        "icon": "🛡️"
    },
    "mage": {
        "hp": 70, "max_hp": 70, "attack": 30,
        "description": "Fragile channeller. Glass cannon — high risk, high reward.",
        "icon": "🔮"
    },
}

# ──────────────────────────────────────────────────────────────────────────────
# Class Skills
# ──────────────────────────────────────────────────────────────────────────────

CLASS_SKILLS = {
    "fighter": [
        {
            "key":         "sword_wave",
            "name":        "Sword Wave",
            "icon":        "🌊",
            "flavor":      "Crescent blade wave · 190% ATK",
            "damage_mult": 1.9,
            "cooldown":    3,
            "vfx":         "slash",
            "color":       "#60a5fa",
        },
        {
            "key":         "dragon_talon",
            "name":        "Dragon Talon",
            "icon":        "🐉",
            "flavor":      "Spiral claw strike · 280% ATK",
            "damage_mult": 2.8,
            "cooldown":    5,
            "vfx":         "dragon",
            "color":       "#fb923c",
        },
    ],
    "tank": [
        {
            "key":         "iron_impact",
            "name":        "Iron Impact",
            "icon":        "🦾",
            "flavor":      "Armored haymaker · 170% ATK · +20 HP",
            "damage_mult": 1.7,
            "cooldown":    3,
            "heal":        20,
            "vfx":         "impact",
            "color":       "#fbbf24",
        },
        {
            "key":         "seismic_slam",
            "name":        "Seismic Slam",
            "icon":        "🌋",
            "flavor":      "Ground-shattering stomp · 260% ATK",
            "damage_mult": 2.6,
            "cooldown":    5,
            "vfx":         "quake",
            "color":       "#f87171",
        },
    ],
    "mage": [
        {
            "key":         "flame_burst",
            "name":        "Flame Burst",
            "icon":        "🔥",
            "flavor":      "Searing fire bolt · 200% ATK",
            "damage_mult": 2.0,
            "cooldown":    3,
            "vfx":         "fire",
            "color":       "#f97316",
        },
        {
            "key":         "dark_void",
            "name":        "Dark Void",
            "icon":        "🌑",
            "flavor":      "Void collapse · 350% ATK · costs 15 HP",
            "damage_mult": 3.5,
            "cooldown":    5,
            "hp_cost":     15,
            "vfx":         "void",
            "color":       "#a855f7",
        },
    ],
}


# ──────────────────────────────────────────────────────────────────────────────
# Combat Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _enemy_max(user: dict) -> int:
    return session.get("enemy_max_hp", max(user["enemy_hp"], 1))


def _enemy_glyph(name: str) -> str:
    """Map enemy name to an emoji glyph for the combat arena."""
    n = name.lower()
    if any(w in n for w in ["wolf", "hound", "stalker", "beast"]):  return "🐺"
    if any(w in n for w in ["wraith", "shade", "hollow"]):          return "👁"
    if any(w in n for w in ["guardian", "sentinel", "warden"]):     return "🗡️"
    if any(w in n for w in ["lieutenant", "lord", "commander"]):    return "💀"
    if any(w in n for w in ["king", "aldrath"]):                    return "👑"
    return "☠️"


def _get_skill(char_class: str, key: str) -> dict | None:
    return next((s for s in CLASS_SKILLS.get(char_class, []) if s["key"] == key), None)


def _tick_cooldowns():
    """Decrement every active cooldown by 1 at end of each combat round."""
    cds = session.get("cooldowns", {})
    session["cooldowns"] = {k: max(0, v - 1) for k, v in cds.items()}


# ──────────────────────────────────────────────────────────────────────────────
# Routes — Auth
# ──────────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return redirect(url_for("dashboard") if "user_id" in session else url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db   = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        db.close()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"]  = user["id"]
            session["username"] = user["username"]
            flash(f"Welcome back, {username}. The Veil awaits.", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid credentials. The shadows reject you.", "error")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username   = request.form.get("username", "").strip()
        password   = request.form.get("password", "")
        char_class = request.form.get("char_class", "fighter")
        if len(username) < 3:
            flash("Username must be at least 3 characters.", "error")
            return render_template("register.html", class_stats=CLASS_STATS)
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("register.html", class_stats=CLASS_STATS)
        if char_class not in CLASS_STATS:
            flash("Invalid class selection.", "error")
            return render_template("register.html", class_stats=CLASS_STATS)
        stats = CLASS_STATS[char_class]
        db    = get_db()
        if db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone():
            db.close()
            flash("That name is already taken.", "error")
            return render_template("register.html", class_stats=CLASS_STATS)
        db.execute(
            """INSERT INTO users
               (username, password_hash, char_class, hp, max_hp, attack,
                current_node, in_combat, enemy_hp, enemy_attack, enemy_name, pending_node)
               VALUES (?, ?, ?, ?, ?, ?, 'start', 0, 0, 0, '', 'start')""",
            (username, generate_password_hash(password),
             char_class, stats["hp"], stats["max_hp"], stats["attack"])
        )
        db.commit()
        db.close()
        flash("Your legend is written. Enter the darkness.", "success")
        return redirect(url_for("login"))
    return render_template("register.html", class_stats=CLASS_STATS)


@app.route("/logout")
def logout():
    session.clear()
    flash("You step back from the Veil. For now.", "info")
    return redirect(url_for("login"))


# ──────────────────────────────────────────────────────────────────────────────
# Routes — Dashboard
# ──────────────────────────────────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    user = get_user(session["user_id"])
    cls  = CLASS_STATS.get(user["char_class"], {})
    return render_template("dashboard.html", user=user, cls=cls)


# ──────────────────────────────────────────────────────────────────────────────
# Routes — Game
# ──────────────────────────────────────────────────────────────────────────────

@app.route("/game")
@login_required
def game():
    user = get_user(session["user_id"])
    if user["hp"] <= 0:
        return redirect(url_for("game_over"))

    node      = get_node(user["current_node"]) or get_node("start")
    cls       = CLASS_STATS.get(user["char_class"], {})
    skills    = CLASS_SKILLS.get(user["char_class"], [])
    cooldowns = session.get("cooldowns", {})

    combat_log = session.pop("combat_log", [])
    last_vfx   = session.pop("last_vfx", None)

    return render_template(
        "game.html",
        user=user, node=node, cls=cls,
        skills=skills, cooldowns=cooldowns,
        combat_log=combat_log, last_vfx=last_vfx,
        hp_pct=int((user["hp"] / user["max_hp"]) * 100),
        enemy_hp_pct=(
            int((user["enemy_hp"] / _enemy_max(user)) * 100)
            if user["in_combat"] else 0
        ),
        enemy_glyph=_enemy_glyph(user["enemy_name"]) if user["in_combat"] else "☠️",
    )


@app.route("/game/action", methods=["POST"])
@login_required
def game_action():
    user = get_user(session["user_id"])
    if user["hp"] <= 0:
        return redirect(url_for("game_over"))

    choice_index = int(request.form.get("choice", 0))
    node         = get_node(user["current_node"])
    if not node or choice_index >= len(node["choices"]):
        return redirect(url_for("game"))

    choice     = node["choices"][choice_index]
    hp_change  = choice.get("hp_change", 0)
    atk_bonus  = choice.get("attack_bonus", 0)
    new_hp     = min(max(user["hp"] + hp_change, 0), user["max_hp"])
    new_attack = user["attack"] + atk_bonus

    if choice.get("triggers_combat"):
        edata      = choice.get("enemy", {})
        names      = edata.get("names", [edata.get("name", "Shadow Beast")])
        enemy_name = random.choice(names)
        enemy_hp   = edata.get("hp", 50)
        enemy_atk  = edata.get("attack", 10)
        next_node  = choice.get("next_node", "crossroads")

        session["enemy_max_hp"] = enemy_hp
        session["cooldowns"]    = {}          # fresh cooldowns each fight

        update_user(session["user_id"],
                    hp=new_hp, attack=new_attack, in_combat=1,
                    enemy_name=enemy_name, enemy_hp=enemy_hp,
                    enemy_attack=enemy_atk, pending_node=next_node)
        session["combat_log"] = [
            f"⚔️  A <strong>{enemy_name}</strong> emerges from the darkness — battle begins!"
        ]
        return redirect(url_for("game"))

    update_user(session["user_id"],
                hp=new_hp, attack=new_attack,
                current_node=choice.get("next_node", "crossroads"),
                in_combat=0)
    if new_hp <= 0:
        return redirect(url_for("game_over"))
    if hp_change > 0:   flash(f"✨ You recover {hp_change} HP.", "heal")
    elif hp_change < 0: flash(f"💀 You lose {abs(hp_change)} HP.", "damage")
    if atk_bonus  > 0:  flash(f"⚔️ Attack increased by {atk_bonus}.", "buff")
    return redirect(url_for("game"))


@app.route("/game/combat", methods=["POST"])
@login_required
def combat_action():
    """One round of combat: skill / attack / defend."""
    user = get_user(session["user_id"])
    if not user["in_combat"]:
        return redirect(url_for("game"))

    action    = request.form.get("action", "attack")
    enemy_hp  = user["enemy_hp"]
    player_hp = user["hp"]
    log       = []

    # ─── SKILL ───────────────────────────────────────────────────────────────
    if action.startswith("skill:"):
        skill_key = action.split(":", 1)[1]
        skill     = _get_skill(user["char_class"], skill_key)
        cooldowns = session.get("cooldowns", {})

        if not skill:
            flash("Unknown skill.", "error")
            return redirect(url_for("game"))
        if cooldowns.get(skill_key, 0) > 0:
            flash(f"{skill['name']} is on cooldown for {cooldowns[skill_key]} more turn(s).", "error")
            return redirect(url_for("game"))

        raw_dmg  = int(user["attack"] * skill["damage_mult"])
        p_dmg    = max(1, raw_dmg + random.randint(-5, 8))
        enemy_hp -= p_dmg
        log.append(
            f"<span class='skill-flash' style='color:{skill['color']}'>"
            f"✦ {skill['icon']} <strong>{skill['name']}</strong></span> — "
            f"<span class='dmg'>{p_dmg}</span> damage!"
        )
        if skill.get("heal"):
            player_hp = min(player_hp + skill["heal"], user["max_hp"])
            log.append(f"💚 Restores <span class='heal'>{skill['heal']}</span> HP.")
        if skill.get("hp_cost"):
            player_hp -= skill["hp_cost"]
            log.append(f"🩸 Costs <span class='dmg'>{skill['hp_cost']}</span> HP to channel.")

        cooldowns[skill_key] = skill["cooldown"]
        session["cooldowns"] = cooldowns
        session["last_vfx"]  = {
            "type": skill["vfx"], "color": skill["color"],
            "name": skill["name"], "icon": skill["icon"]
        }

        if enemy_hp <= 0:
            log.append(f"💀 <strong>{user['enemy_name']}</strong> is obliterated!")
            _tick_cooldowns()
            session["combat_log"] = log
            session.pop("enemy_max_hp", None)
            update_user(session["user_id"],
                        hp=max(player_hp, 0), in_combat=0,
                        enemy_hp=0, current_node=user["pending_node"])
            if player_hp <= 0:
                return redirect(url_for("game_over"))
            flash(f"Victory! {user['enemy_name']} falls.", "success")
            return redirect(url_for("game"))

        e_dmg     = max(1, user["enemy_attack"] + random.randint(-3, 4))
        player_hp -= e_dmg
        log.append(
            f"🩸 <strong>{user['enemy_name']}</strong> retaliates — "
            f"<span class='dmg'>{e_dmg}</span> damage."
        )

    # ─── BASIC ATTACK ────────────────────────────────────────────────────────
    elif action == "attack":
        p_dmg    = max(1, user["attack"] + random.randint(-4, 6))
        enemy_hp -= p_dmg
        log.append(
            f"⚔️  You strike <strong>{user['enemy_name']}</strong> for "
            f"<span class='dmg'>{p_dmg}</span> damage."
        )
        session["last_vfx"] = {"type": "attack", "color": "#f0ead8",
                                "name": "Strike", "icon": "⚔️"}

        if enemy_hp <= 0:
            log.append(f"💀 <strong>{user['enemy_name']}</strong> crumbles into shadow dust!")
            _tick_cooldowns()
            session["combat_log"] = log
            session.pop("enemy_max_hp", None)
            update_user(session["user_id"],
                        in_combat=0, enemy_hp=0, current_node=user["pending_node"])
            flash("Victory! The enemy is slain.", "success")
            return redirect(url_for("game"))

        e_dmg     = max(1, user["enemy_attack"] + random.randint(-3, 4))
        player_hp -= e_dmg
        log.append(
            f"🩸 <strong>{user['enemy_name']}</strong> retaliates — "
            f"<span class='dmg'>{e_dmg}</span> damage."
        )

    # ─── DEFEND ──────────────────────────────────────────────────────────────
    elif action == "defend":
        e_dmg     = max(1, random.randint(1, max(1, user["enemy_attack"] // 2)))
        player_hp -= e_dmg
        log.append(f"🛡️  You brace — absorbing only <span class='dmg'>{e_dmg}</span> damage.")
        riposte   = max(1, user["attack"] // 4 + random.randint(0, 3))
        enemy_hp -= riposte
        log.append(f"↩️  Riposte strikes for <span class='heal'>{riposte}</span> damage.")
        session["last_vfx"] = {"type": "defend", "color": "#6ee7b7",
                                "name": "Guard", "icon": "🛡️"}

        if enemy_hp <= 0:
            log.append(f"💀 <strong>{user['enemy_name']}</strong> falls to your riposte!")
            _tick_cooldowns()
            session["combat_log"] = log
            session.pop("enemy_max_hp", None)
            update_user(session["user_id"],
                        hp=max(player_hp, 0), in_combat=0,
                        enemy_hp=0, current_node=user["pending_node"])
            if player_hp <= 0:
                return redirect(url_for("game_over"))
            flash("Victory! The enemy is slain.", "success")
            return redirect(url_for("game"))

    # ─── End of round ────────────────────────────────────────────────────────
    _tick_cooldowns()
    session["combat_log"] = log

    if player_hp <= 0:
        update_user(session["user_id"], hp=0, in_combat=0)
        return redirect(url_for("game_over"))

    update_user(session["user_id"], hp=player_hp, enemy_hp=enemy_hp)
    return redirect(url_for("game"))


# ──────────────────────────────────────────────────────────────────────────────
# Routes — Game Over & Restart
# ──────────────────────────────────────────────────────────────────────────────

@app.route("/game/over")
@login_required
def game_over():
    user = get_user(session["user_id"])
    cls  = CLASS_STATS.get(user["char_class"], {})
    return render_template("game_over.html", user=user, cls=cls)


@app.route("/game/restart", methods=["POST"])
@login_required
def restart_game():
    user  = get_user(session["user_id"])
    stats = CLASS_STATS[user["char_class"]]
    update_user(session["user_id"],
                hp=stats["hp"], max_hp=stats["max_hp"], attack=stats["attack"],
                current_node="start", in_combat=0,
                enemy_hp=0, enemy_attack=0, enemy_name="", pending_node="start")
    session.pop("combat_log", None)
    session.pop("enemy_max_hp", None)
    session.pop("cooldowns", None)
    session.pop("last_vfx", None)
    flash("The Veil resets. Your story begins anew.", "info")
    return redirect(url_for("game"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
