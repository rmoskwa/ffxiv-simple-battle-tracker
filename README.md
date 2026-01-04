# FFXIV Battle Tracker

A simplified Advanced Combat Tracker (ACT) log file parser to extract information that I care about and presents it through an interactive web dashboard. Parses and displays ability hits, debuffs, deaths, targeting events, and tables showing who got hit by what across all pulls in a lockout. Calculates unmitigated damage by tracking active mitigations and shields. Is able to present a rudimentary timeline.

This parser is not as exhaustive as what FFlogs uses to generate their reports. Only these log line types are handled:

| Line Type | Name           | Purpose                                                                |
|-----------|----------------|------------------------------------------------------------------------|
| 01        | Zone Change    | Detects entering/leaving raid instances                                |
| 03        | AddCombatant   | Identifies players and enemies (tracks IDs, names, jobs, HP)           |
| 20        | StartsCasting  | Boss→player cast targeting (who the boss is casting on)                |
| 21/22     | NetworkAbility | Enemy→player ability damage (21=single target, 22=AOE)                 |
| 25        | NetworkDeath   | Player deaths (who died and what killed them)                          |
| 26        | NetworkBuff    | Debuffs (boss→player), mitigations (player buffs), boss debuffs (Reprisal, etc.) |
| 27        | HeadMarker     | Visual markers placed on players (spread, stack, flare, etc.)          |
| 33        | ActorControl   | Fight state signals (commence, wipe, victory, barrier up)              |
| 37        | EffectResult   | Post-ability HP/shield values for shield absorption calculations       |

This means that timeline generation is not fully accurate, as Abilities and Debuffs will only be parsed if a player is affected by them. Actions such as "Boss prepares X cast" or channeled abilities won't always be presented. However, the purpose of this application is to understand what is hitting players, how often, and who gets consistently targeted, so a simplified parsing scheme suffices. 

## Installation

Requires Python 3.10+

```bash
# Clone the repository
git clone https://github.com/rmoskwa/ffxiv-simple-battle-tracker.git
cd ffxiv-battle-tracker

# Create and activate a virtual environment
python -m venv .venv
source .venv\Scripts\activate # Ubuntu
# OR
.\.venv\Scripts\Activate.ps1 # Windows

# Install from pyproject.toml
pip install -e .

# For development (includes ruff, pytest, pre-commit)
pip install -e ".[dev]"
```

## Usage

### GUI (Recommended for most users)

```bash
ffxiv-tracker
```

This opens a graphical launcher where you can:
- Browse and select your ACT log file
- Set a custom port (default: 8080)
- Click "Launch" to parse and start the web dashboard
- Click "View in Browser" to open the dashboard
- Settings are remembered between sessions

### Command Line

```bash
# Parse a log file (CLI output)
ffxiv-tracker --parse /path/to/log.log # Useful for a sanity check to see if parser is working

# Parse with web dashboard
ffxiv-tracker --parse /path/to/log.log --web

# Custom port
ffxiv-tracker --parse /path/to/log.log --web --port 9000

# Verbose output
ffxiv-tracker --parse /path/to/log.log -v
```

## Tech Stack

**Backend:** Python 3.10+ with Flask

**Frontend:** Vanilla JavaScript with HTML/CSS

**Architecture:**

- **State Machine Parser** - Processes ACT log files through states: IDLE → IN_INSTANCE → IN_COMBAT → WIPE_PENDING
- **Line Handlers** - Parse specific ACT log line types (zone changes, combatants, abilities, deaths, buffs)
- **REST API** - Flask endpoints expose parsed data for the dashboard
- **Interactive Dashboard** - Web UI for visualizing fight data and player metrics

**Repository Structure:**

```
src/
├── main.py                 # CLI entry point
├── gui_launcher.py         # GUI launcher (tkinter)
├── models/
│   └── data_models.py      # Data structures (Player, FightAttempt, RaidSession, etc.)
├── parser/
│   ├── log_parser.py       # State machine log parser
│   ├── line_handlers.py    # ACT log line parsing
│   └── damage_calc.py      # Hex-encoded damage decoding
├── data/
│   └── mitigation_db.py    # Mitigation and boss debuff definitions
└── web/
    └── server.py           # Flask REST API

static/
├── css/
│   └── styles.css          # Dashboard styling
└── js/
    └── dashboard.js        # Interactive dashboard

templates/
└── index.html              # Dashboard HTML template

tests/
├── test_damage_calc.py     # Damage calculation tests
├── test_line_handlers.py   # Log line parsing tests
└── test_log_parser.py      # Parser state machine tests
```
