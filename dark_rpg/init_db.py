"""
init_db.py — Initialize the SQLite database, create tables,
seed test accounts, and populate all story nodes.

Run once before starting the app:
    python init_db.py
"""

import sqlite3
import json
from werkzeug.security import generate_password_hash

DB_PATH = "game.db"

# ──────────────────────────────────────────────────────────────────────────────
# Schema
# ──────────────────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    UNIQUE NOT NULL,
    password_hash TEXT    NOT NULL,
    char_class    TEXT    NOT NULL DEFAULT 'fighter',
    hp            INTEGER NOT NULL DEFAULT 100,
    max_hp        INTEGER NOT NULL DEFAULT 100,
    attack        INTEGER NOT NULL DEFAULT 15,
    current_node  TEXT    NOT NULL DEFAULT 'start',
    in_combat     INTEGER NOT NULL DEFAULT 0,
    enemy_hp      INTEGER NOT NULL DEFAULT 0,
    enemy_attack  INTEGER NOT NULL DEFAULT 0,
    enemy_name    TEXT    NOT NULL DEFAULT '',
    pending_node  TEXT    NOT NULL DEFAULT 'start'
);

CREATE TABLE IF NOT EXISTS story_nodes (
    node_id   TEXT PRIMARY KEY,
    title     TEXT NOT NULL,
    text      TEXT NOT NULL,
    choices   TEXT NOT NULL DEFAULT '[]',
    node_type TEXT NOT NULL DEFAULT 'story'
);
"""

# ──────────────────────────────────────────────────────────────────────────────
# Test Accounts
# ──────────────────────────────────────────────────────────────────────────────

TEST_USERS = [
    {
        "username": "fighter",
        "password": "fighter123",
        "char_class": "fighter",
        "hp": 120, "max_hp": 120, "attack": 18,
    },
    {
        "username": "tank",
        "password": "tank123",
        "char_class": "tank",
        "hp": 200, "max_hp": 200, "attack": 10,
    },
    {
        "username": "mage",
        "password": "mage123",
        "char_class": "mage",
        "hp": 70, "max_hp": 70, "attack": 30,
    },
]

# ──────────────────────────────────────────────────────────────────────────────
# Story Nodes
# ──────────────────────────────────────────────────────────────────────────────
# Each node has:
#   node_id   — unique string key
#   title     — short display title
#   text      — immersive narrative (HTML allowed: <p>, <em>, <strong>)
#   choices   — JSON list of choice objects:
#       {
#           "text":             display text for button,
#           "next_node":        node_id to navigate to (or pending_node if combat),
#           "hp_change":        HP delta on selection (negative = damage),
#           "attack_bonus":     permanent attack stat increase,
#           "triggers_combat":  bool — starts a combat encounter,
#           "enemy": {
#               "names":  list of possible names (random pick),
#               "hp":     enemy starting HP,
#               "attack": enemy attack stat
#           }
#       }
#   node_type — "story" | "ending"
# ──────────────────────────────────────────────────────────────────────────────

def c(text, next_node, hp_change=0, attack_bonus=0,
      triggers_combat=False, enemy=None):
    """Shorthand choice builder."""
    obj = {
        "text": text,
        "next_node": next_node,
        "hp_change": hp_change,
        "attack_bonus": attack_bonus,
        "triggers_combat": triggers_combat,
    }
    if enemy:
        obj["enemy"] = enemy
    return obj


STORY_NODES = [

    # ── ACT I: AWAKENING ─────────────────────────────────────────────────────

    {
        "node_id": "start",
        "title": "The Awakening",
        "node_type": "story",
        "text": """
<p>The ground is cold. Stone. Ancient stone fractured by time and darker forces.</p>

<p>You open your eyes to a world consumed by perpetual twilight — a twilight that has lasted three years.</p>

<p>You are in the ruins of <strong>Valdrath</strong>, once the gleaming capital of the Kingdom of Solmere. The towers that touched the clouds lie shattered. The streets where merchant guilds once sang now drift with black ash and the distant howl of creatures that used to be men.</p>

<p>You are one of the <strong>Bound</strong>.</p>

<p>Where others collapsed beneath the <em>Veil</em> — that creeping darkness which bled from the Ashen Mountains and swallowed the kingdom whole — you did not. The ancient sigil burned into your left wrist pulses faintly gold against the surrounding dark. A blessing from gods who no longer answer prayers. Or perhaps a sentence.</p>

<p>You pull yourself upright. Your weapons are still with you. Your will is intact. Somewhere deep within the ruined city, the Veil's heart beats like a second sun — black, cold, and growing stronger.</p>

<p>You are the last Bound. If the Veil is not severed here, it will spread beyond these borders and consume everything.</p>

<p><em>It is time to move.</em></p>
""",
        "choices": [
            c("Rise. Face what remains.", "crossroads"),
        ],
    },

    {
        "node_id": "crossroads",
        "title": "The Shattered Crossroads",
        "node_type": "story",
        "text": """
<p>You stand at what was once Valdrath's grand crossroads — the marble statue of the First King toppled, his stone face half-buried in the ash. Four roads radiate outward. Two are fully consumed by the Veil's black tendrils, impassable and writhing.</p>

<p>Two remain open, barely.</p>

<p>To the <strong>north</strong>, the road disappears into <em>Thornwood Forest</em>, the ancient woodland that borders the city. Normally silver-leafed and serene, it now twists in purple shadow, the trees grown angular and wrong. Strange sounds echo from within — not all of them animal.</p>

<p>To the <strong>east</strong>, the road cuts through the remnants of <em>Ashenmere</em>, the merchant district. Collapsed colonnades and gutted towers line the approach. It's quieter than the forest — but silence in Valdrath is rarely a good sign.</p>

<p>Your sigil burns on both paths equally. The Veil is everywhere.</p>
""",
        "choices": [
            c("Head north into Thornwood Forest.", "thornwood_entrance"),
            c("Head east through the ruins of Ashenmere.", "ashenmere_entrance"),
        ],
    },

    # ── ACT I — THORNWOOD PATH ───────────────────────────────────────────────

    {
        "node_id": "thornwood_entrance",
        "title": "Thornwood's Dark Heart",
        "node_type": "story",
        "text": """
<p>The forest closes over you like a wound sealing shut. Once, Thornwood was a place of silver birches and wandering deer. Now the bark is jet-black, the branches overhead form an interlocking cage, and the light that filters through is the deep violet of a bruise.</p>

<p>The path is still visible — barely. Someone has walked it recently. Boot prints press into the dark soil, and beside them, deep gouges from something with claws.</p>

<p>A low sound rolls through the undergrowth. Not wind. Not bark settling. Something breathes in the dark ahead, and whatever it is, it has already noticed you.</p>
""",
        "choices": [
            c(
                "Draw your weapon and press forward — face whatever lurks ahead.",
                "ancient_shrine",
                triggers_combat=True,
                enemy={
                    "names": ["Shadow Wolf", "Veil Hound", "Thornwood Stalker"],
                    "hp": 52,
                    "attack": 14,
                }
            ),
            c(
                "Slip off the path, moving silently through the underbrush.",
                "thornwood_skulk",
                hp_change=-15,
            ),
        ],
    },

    {
        "node_id": "thornwood_skulk",
        "title": "The Unseen Trail",
        "node_type": "story",
        "text": """
<p>You ghost through the undergrowth, making no sound, trusting instinct over sight. For a long stretch it works — the creature on the path stalks past within feet of you, its rotting breath steaming in the cold air, its silhouette wrong in ways you struggle to define.</p>

<p>Then a branch snaps beneath your boot.</p>

<p>The creature wheels. You run. It gives chase — not far, but long enough that by the time you pull ahead and break into a moonlit clearing, your side is bleeding from where claws grazed you, and your heart hammers like a war drum.</p>

<p>The creature retreats into the dark, unwilling to leave the canopy's shade. You stand gasping at the edge of a clearing dominated by an ancient moss-covered altar.</p>
""",
        "choices": [
            c("Approach the altar — investigate the ancient stones.", "ancient_shrine"),
        ],
    },

    {
        "node_id": "ancient_shrine",
        "title": "The Shrine of the Old Gods",
        "node_type": "story",
        "text": """
<p>A circle of standing stones surrounds a cracked obsidian altar. The stones are carved with a script you half-recognise — Solmerian, the tongue of the First Kingdom. Old enough that even the scholars had trouble reading it.</p>

<p>But your sigil understands. It pulses warmly as you approach, and the carvings seem to shift, resolve, whisper:</p>

<p><em>"The Bound shall endure. That which is offered shall be returned."</em></p>

<p>At the altar's centre sits a cracked stone bowl. A flicker of golden light still pools in it, impossibly sustained. Beside it, jutting from a split in the stone, is a jagged shard of something dark — a fragment of a greater weapon, perhaps, or an old god's fallen idol. It radiates a cold, focused hunger.</p>

<p>You cannot take both. The shrine's power does not work that way.</p>
""",
        "choices": [
            c(
                "Cup your hands in the golden light — accept the shrine's healing.",
                "veil_approach",
                hp_change=35,
            ),
            c(
                "Claim the dark shard — bind its power to your weapon.",
                "veil_approach",
                attack_bonus=8,
            ),
        ],
    },

    # ── ACT I — ASHENMERE PATH ───────────────────────────────────────────────

    {
        "node_id": "ashenmere_entrance",
        "title": "Ruins of Ashenmere",
        "node_type": "story",
        "text": """
<p>The merchant quarter is a graveyard of wealth. Collapsed market stalls, cracked flagstones, the skeletal remains of shops that once sold spices and silk and stolen gods. Everything is coated in grey ash that muffles every footstep like fresh snow.</p>

<p>Most of the bodies you pass are empty of shadow — whatever the Veil did to them, it did it quickly. That's something.</p>

<p>Halfway through the district, you notice two things simultaneously: movement near the shattered fountain at the plaza's heart, and the collapsed skeleton of the old merchant guild hall to your left, its vaulted roof partly standing, its bronze doors still sealed.</p>
""",
        "choices": [
            c("Investigate the movement near the fountain.", "survivor_meeting"),
            c("Break into the merchant guild hall and search for supplies.", "merchant_ruins"),
        ],
    },

    {
        "node_id": "survivor_meeting",
        "title": "The Last Cartographer",
        "node_type": "story",
        "text": """
<p>The figure by the fountain is small, wrapped in so many cloaks they seem more bundle than person. When you approach, they spin around with a knife raised — then lower it, exhaling sharply.</p>

<p><strong>"Bound,"</strong> the old woman breathes, squinting at your glowing sigil. <em>"I thought they were all dead. The shadows don't take the Bound, do they."</em> She says it as fact, not question.</p>

<p>Her name is <strong>Sera</strong>. Former royal cartographer. She has survived by staying moving, sleeping in different ruins each night, eating from stores buried under collapsed floors. She knows the city's geography better than anyone alive — which, she notes with grim humour, isn't saying much.</p>

<p>She presses a flask of broth and a folded map into your hands. <em>"The Veil's gate is at the old Palace grounds — northeast. But something changed four days ago. The darkness pulsed. Whatever's at the centre, it's… growing. You'll need to move fast."</em></p>

<p>She refuses to come with you. You don't push.</p>
""",
        "choices": [
            c(
                "Thank Sera, drink the broth, and move northeast toward the Veil.",
                "veil_approach",
                hp_change=25,
            ),
        ],
    },

    {
        "node_id": "merchant_ruins",
        "title": "Buried Wealth, Buried Bones",
        "node_type": "story",
        "text": """
<p>The guild hall is dark and smells of old metal and rot. Bronze plaques on the walls still name the great merchant houses — families whose descendants are now shadow or ash. Irony, that their building survived when they did not.</p>

<p>You work through collapsed shelves and overturned strongboxes. Most have been gutted already — by survivors, by looters who didn't survive. But beneath a false floor in the master merchant's office, you find two caches.</p>

<p>The first: a rack of fine weapons — blades of Solmerian steel, still oiled, still sharp, enchanted faintly to hold an edge. You could retool your own weapon with these components.</p>

<p>The second: a sealed crate of field medicine — poultices, spirits, and three full doses of <em>Vitaelixir</em>, the old military restorative. Worth its weight in lives during the Veil's first weeks. Still potent.</p>

<p>The shelf groans above you. You have time for one.</p>
""",
        "choices": [
            c(
                "Take the weapons cache — adapt the Solmerian steel to your armament.",
                "veil_approach",
                attack_bonus=7,
            ),
            c(
                "Take the medicine — your body will thank you later.",
                "veil_approach",
                hp_change=45,
            ),
        ],
    },

    # ── ACT II: THE VEIL'S EDGE ───────────────────────────────────────────────

    {
        "node_id": "veil_approach",
        "title": "The Edge of the Veil",
        "node_type": "story",
        "text": """
<p>The palace grounds come into view as the road crests a broken hill, and the sight of it stops you dead.</p>

<p>The Veil is not the creeping, formless thing the stories described when it first appeared. It has consolidated — a towering wall of absolute darkness that rises from the palace's outer courtyard straight up into the clouds, the top lost to blackness. Its surface is not still. It churns. It breathes. In its depth you can see shapes moving, glimpsed and then gone.</p>

<p>Your sigil flares painfully bright. It has never burned like this.</p>

<p>To your left, half-buried under a collapsed garden wall, the carved stone lintel of the old <strong>Reliquary of the Bound</strong> is still visible — the underground vault where Solmere's warriors sealed their greatest weapons before the final battle. No one retrieved them. Most assumed it was looted or destroyed.</p>

<p>The Veil's gate pulses ahead, waiting. Time feels short.</p>
""",
        "choices": [
            c(
                "Enter the Veil directly — no more preparation, no more delay.",
                "veil_interior",
            ),
            c(
                "Excavate the Reliquary — the Bound left weapons for exactly this purpose.",
                "reliquary_path",
            ),
        ],
    },

    {
        "node_id": "reliquary_path",
        "title": "The Reliquary of the Bound",
        "node_type": "story",
        "text": """
<p>The vault's entrance is sealed by three interlocked stones, each bearing a Bound sigil. When you press your wrist to them, they unlock with a resonance that shakes dust from the ceiling and sets your bones vibrating.</p>

<p>Inside: a long corridor lined with glass cases, each holding the weapon of a fallen Bound warrior. Swords. Staves. An archer's brace. Their names are engraved in the floor beneath each case.</p>

<p>At the corridor's end, on a dais of white stone, floats the <strong>Relic of Binding</strong> — a crystalline seal roughly the size of your fist, rotating slowly, humming with stored power. The inscriptions around its dais translate, roughly, to: <em>"That which bound the First Darkness shall bind the Last."</em></p>

<p>But the Relic is not alone. A figure stands before the dais — tall, armoured in the old Bound style, but wrong. Its eyes are black voids. It has been waiting in this vault for three years, corrupted by proximity to the Veil, still fulfilling its last order: <em>guard.</em></p>
""",
        "choices": [
            c(
                "Fight the Corrupted Guardian — claim the Relic of Binding.",
                "relic_obtained",
                triggers_combat=True,
                enemy={
                    "names": ["Corrupted Bound Guardian", "Fallen Sentinel", "Veil-Touched Warden"],
                    "hp": 72,
                    "attack": 17,
                }
            ),
            c(
                "Retreat from the vault — the Relic isn't worth the fight.",
                "veil_approach",
            ),
        ],
    },

    {
        "node_id": "relic_obtained",
        "title": "The Relic Awakens",
        "node_type": "story",
        "text": """
<p>The Guardian falls. Its armour rings against the stone floor, and for a moment you see something — a face, human, confused, grateful — before it dissolves into ash and the vault falls silent.</p>

<p>The Relic of Binding descends from its hover to rest in your open palm. It is heavier than it looks. It is warmer than it has any right to be. The crystal surface is covered in micro-engravings of every Bound warrior who ever lived, a tiny etched history of everyone who stood against the dark.</p>

<p>Your sigil synchronises with it — a brilliant flare of gold light, and when it fades, you feel the power woven into your grip. Your weapon, your body, your intent: all of it sharpened by something that was made precisely for this moment.</p>

<p>The inscriptions have changed. Now they read: <em>"One seal. One chance. Use it well."</em></p>
""",
        "choices": [
            c(
                "Bind the Relic to your weapon and advance toward the Veil.",
                "veil_interior",
                attack_bonus=15,
            ),
        ],
    },

    # ── ACT III: WITHIN THE VEIL ─────────────────────────────────────────────

    {
        "node_id": "veil_interior",
        "title": "Within the Veil",
        "node_type": "story",
        "text": """
<p>Crossing the Veil's boundary is like stepping through freezing water made of silence. The world outside — the ash, the ruins, the grey sky — vanishes entirely.</p>

<p>Inside is not darkness. It is something worse: a perfect replica of Valdrath as it was before the fall, rendered in shades of grey and deep blue, like a memory preserved in ice. Ghostly figures walk the streets in their old patterns, soldiers march routes they marched three years ago, children run through a square that exists only here.</p>

<p>They do not see you. They are not real.</p>

<p>The only truly present thing is the weight in the air — pressure building, pressing inward — and the Shadow Wraith that detaches from the palace gate ahead, unfurling like smoke given malice and intention. It moves with terrible grace toward you, its hollow face fixed on your glowing sigil.</p>

<p>Behind it, the palace doors. Behind those: the source of everything.</p>
""",
        "choices": [
            c(
                "Engage the Shadow Wraith — cut through it and advance.",
                "throne_approach",
                triggers_combat=True,
                enemy={
                    "names": ["Shadow Wraith", "Veil Shade", "Screaming Hollow"],
                    "hp": 85,
                    "attack": 21,
                }
            ),
            c(
                "Attempt to slip past using the ghost-crowd as cover.",
                "veil_detour",
            ),
        ],
    },

    {
        "node_id": "veil_detour",
        "title": "The Shadow's Memory",
        "node_type": "story",
        "text": """
<p>You step into the flow of ghostly citizens and march with them, matching their rhythm, keeping your sigil pressed against your thigh to dim its glow. The Wraith circles. Searches. Passes within arm's reach.</p>

<p>Then a ghost walks through you — and it stops. In the moment of contact you experience its memory: the last day before the Veil fell. A family, a meal, a sunset. The raw ordinary joy of it hits like a physical blow, and for a second you cannot breathe.</p>

<p>When you surface from the memory, the Wraith is gone. But the contact has left something behind — a resonance, a ghost-echo in your sigil that seems to sharpen your understanding of the Veil's weaving. You know, somehow, where its seams are. Where to strike.</p>

<p>The palace doors stand open ahead.</p>
""",
        "choices": [
            c(
                "Push through — absorb the resonance and continue into the palace.",
                "throne_approach",
                attack_bonus=5,
                hp_change=-20,
            ),
        ],
    },

    # ── ACT IV: THE THRONE ───────────────────────────────────────────────────

    {
        "node_id": "throne_approach",
        "title": "The Throne's Antechamber",
        "node_type": "story",
        "text": """
<p>The palace interior is not a ghost-memory like the streets outside. It is fully real, fully dark. The Veil has claimed this place absolutely.</p>

<p>In the antechamber — once gilded, now black glass from floor to ceiling — waits <strong>Mordechai, the Dark Lieutenant</strong>. He was the King's Lord Commander. He was the last defender. He was the first to break.</p>

<p>He stands in full armour that has grown into him, shadow-metal fused to bone. His sword is drawn. His eyes are twin voids. But when he speaks, his voice still carries the ghost of a man.</p>

<p><em>"You shouldn't be here. Nothing should be here anymore. The King said — the King promised —"</em></p>

<p>He stops. Shakes his head slowly. Raises his blade.</p>

<p><em>"This ends the same way it always ends."</em></p>
""",
        "choices": [
            c(
                "Raise your weapon. 'Not this time, Mordechai.' — Attack.",
                "shadow_throne",
                triggers_combat=True,
                enemy={
                    "names": ["Mordechai, Dark Lieutenant", "The Broken Lord Commander"],
                    "hp": 110,
                    "attack": 24,
                }
            ),
            c(
                "Try to reach whatever remains of the man inside.",
                "throne_appeal",
            ),
        ],
    },

    {
        "node_id": "throne_appeal",
        "title": "The Last Humanity",
        "node_type": "story",
        "text": """
<p>You lower your weapon. Not far — not foolishly — but enough to signal that you are not leading with steel.</p>

<p><em>"Mordechai. You know what this is."</em> You press your sigil toward him. <em>"The Veil doesn't just take strength. It takes memory. It takes meaning. You're still fighting because some part of you knows this is wrong."</em></p>

<p>The Lieutenant goes very still.</p>

<p>For a long moment, the shadow-metal shifts against his skin, and you see the face beneath — old, haggard, hollowed by years of servitude to something he could not resist. His sword trembles.</p>

<p><em>"...the King didn't fall,"</em> he whispers. <em>"The King chose this. He invited the Veil. He wanted to live forever. He—"</em></p>

<p>The shadow surges. His eyes go black again. He screams — not in rage, but in grief — and attacks.</p>

<p>The truth, at least, is out.</p>
""",
        "choices": [
            c(
                "Defend yourself — honour what he was while fighting what he became.",
                "shadow_throne",
                triggers_combat=True,
                enemy={
                    "names": ["Mordechai, Shattered Lord"],
                    "hp": 90,
                    "attack": 20,
                }
            ),
        ],
    },

    # ── ACT V: THE SHADOW THRONE ─────────────────────────────────────────────

    {
        "node_id": "shadow_throne",
        "title": "Before the Shadow Throne",
        "node_type": "story",
        "text": """
<p>The throne room is vast. Was vast. Now it exists in two states simultaneously — the gilded hall of Solmere's greatest kings, and the absolute nothing of the Veil, both layered over each other, both real and neither real.</p>

<p>On the throne sits <strong>the Shadow King</strong>.</p>

<p>He was King Aldrath the Third. He was fifty-three years old with a bad knee and a love of astronomy when he opened the door that ended the world. He does not look fifty-three now. He does not look human. The Veil has woven itself through him so completely that where he ends and it begins is no longer a meaningful distinction.</p>

<p>He opens his eyes — not black, like his servants, but gold. The gold of a trapped thing that still remembers wanting to live.</p>

<p><em>"Bound,"</em> he says. His voice is the sound of a great building collapsing slowly. <em>"You've come to end me."</em></p>

<p><em>"Or seal the Veil,"</em> you say.</p>

<p>He is silent for a long moment. Then: <em>"They are the same thing."</em></p>

<p>You have the Relic of Binding in your hands. You feel its weight, its warmth, its purpose. It was made for exactly this moment, and it has one use.</p>

<p>But a weapon is also a weapon. And the King is already standing.</p>
""",
        "choices": [
            c(
                "Raise the Relic — drive it into the Veil's heart and seal everything.",
                "ending_seal",
            ),
            c(
                "Draw steel — destroy the Shadow King directly, then seal the Veil.",
                "ending_battle",
                triggers_combat=True,
                enemy={
                    "names": ["King Aldrath, the Shadow Throne", "The Veil-King", "Aldrath the Undying"],
                    "hp": 160,
                    "attack": 32,
                }
            ),
        ],
    },

    # ── ENDINGS ───────────────────────────────────────────────────────────────

    {
        "node_id": "ending_seal",
        "title": "The Veil Closes",
        "node_type": "ending",
        "text": """
<p>You drive the Relic into the floor at the throne room's centre and speak the binding word — not a word you were taught, but a word your sigil has always known, burning in the mark since the day it was given to you.</p>

<p>The Relic shatters.</p>

<p>The light it releases is not golden. It is every colour and none, a colour that has no name in any language, a colour that means <em>over</em> and <em>done</em> and <em>not anymore.</em></p>

<p>King Aldrath does not fight it. He closes his gold eyes. When the light reaches him, the shadow peels away like bark from a dying tree, and for just a moment — a fraction of a heartbeat — you see the man he was. Tired. Old. Genuinely sorry.</p>

<p>Then the Veil collapses.</p>

<p>It does not collapse gently. It tears itself apart from the inside with a sound like a continent cracking. Every shadow-creature, every Wraith, every corrupted soldier — they unravel simultaneously, rising as black ash on a wind that comes from nowhere and goes everywhere.</p>

<p>The throne room fills with sunlight. Real sunlight. The first any part of Valdrath has seen in three years.</p>

<p>You are still standing. The sigil on your wrist is dark — spent, silent, done. Your purpose, fulfilled.</p>

<p>From somewhere in the ruined city, very distant, you hear a voice shout. Then two voices. Then many.</p>

<p>The survivors are coming out.</p>

<hr>

<p class="ending-coda"><em>The Veil is sealed. Solmere will not be rebuilt in a generation — but it will be rebuilt. And they will remember that when the world ended, one Bound warrior walked into the dark and did not come back until it was over.</em></p>

<p class="ending-coda"><strong>You are that warrior.</strong></p>
""",
        "choices": [],
    },

    {
        "node_id": "ending_battle",
        "title": "The Shadow Falls",
        "node_type": "ending",
        "text": """
<p>The Shadow King falls.</p>

<p>It takes everything — every ounce of skill, every adaptation you made on the road here, every cost you paid across the ruined city. But he falls. The throne that was his for three years of darkness buckles and shatters as the Veil loses its anchor, and where Aldrath the Third knelt in the rubble, only a man-shaped depression of ash remains.</p>

<p>The Relic of Binding trembles in your hand — still whole, still ready. You press it to the palace floor and speak the word.</p>

<p>The Veil unravels.</p>

<p>Faster than you expected. Without its King it is architecture without a builder — magnificent and meaningless. The shadows peel from the stones of Valdrath and dissolve into the morning that has been waiting three years to return. The ghost-memories in the Veil's interior fade gently, gracefully, the people who were preserved in them finally allowed to rest.</p>

<p>You walk out of the palace into a city that smells like rain on old stone and nothing else. Clean. Simple. Impossible.</p>

<p>Your sigil is silent on your wrist. Not dark — just resting. You have the feeling it will wake again, one day, if you are needed.</p>

<p>But not today.</p>

<p>Today is for the living.</p>

<hr>

<p class="ending-coda"><em>The Shadow King is slain. The Veil is broken. Solmere's long night is over — and the Bound warrior who ended it steps, quietly, into the first dawn in three years.</em></p>

<p class="ending-coda"><strong>Your legend is complete.</strong></p>
""",
        "choices": [],
    },
]


# ──────────────────────────────────────────────────────────────────────────────
# Seeding Functions
# ──────────────────────────────────────────────────────────────────────────────

def init_db():
    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create tables
    cursor.executescript(SCHEMA)
    print("✓ Tables created.")

    # Seed test users (skip if already exist)
    for u in TEST_USERS:
        existing = cursor.execute(
            "SELECT id FROM users WHERE username = ?", (u["username"],)
        ).fetchone()
        if existing:
            print(f"  ~ User '{u['username']}' already exists, skipping.")
            continue
        cursor.execute(
            """INSERT INTO users
               (username, password_hash, char_class, hp, max_hp, attack,
                current_node, in_combat, enemy_hp, enemy_attack, enemy_name, pending_node)
               VALUES (?, ?, ?, ?, ?, ?, 'start', 0, 0, 0, '', 'start')""",
            (
                u["username"],
                generate_password_hash(u["password"]),
                u["char_class"],
                u["hp"], u["max_hp"], u["attack"],
            )
        )
        print(f"  ✓ Seeded user '{u['username']}' ({u['char_class']}).")

    # Seed story nodes (replace on conflict for easy re-seeding)
    for node in STORY_NODES:
        cursor.execute(
            """INSERT OR REPLACE INTO story_nodes
               (node_id, title, text, choices, node_type)
               VALUES (?, ?, ?, ?, ?)""",
            (
                node["node_id"],
                node["title"],
                node["text"],
                json.dumps(node["choices"]),
                node.get("node_type", "story"),
            )
        )
    print(f"  ✓ Seeded {len(STORY_NODES)} story nodes.")

    conn.commit()
    conn.close()
    print("\n✓ Database initialised successfully.")
    print("  Run with: python app.py")


if __name__ == "__main__":
    init_db()
