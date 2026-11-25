import hashlib
import hmac
import html
import json
import os
import random
import re
import secrets
import tempfile
import uuid
from collections import Counter
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
import streamlit as st

# ============================================================
# MindMitra - Cognitive Wellness and Brain Games
# Run with: python -m streamlit run mindmitra.py
# Needs: streamlit (1.50 or newer recommended), pandas
# ============================================================

st.set_page_config(
    page_title="MindMitra | Cognitive Wellness",         
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)
PROGRESS_FILE = DATA_DIR / "progress.json"

PAGES = [
    "Home",
    "Memory Games",
    "Number Games",
    "Word Games",
    "My Progress",
    "Caregiver Dashboard",
    "About",
]
GAME_PAGES = ["Memory Games", "Number Games", "Word Games"]
LEVELS = {"Easy": 3, "Medium": 5, "Challenge": 7}
TEAL = "#087F75"


def _streamlit_version():
    try:
        return tuple(int(x) for x in st.__version__.split(".")[:2])
    except ValueError:
        return (0, 0)


# Newer Streamlit replaced use_container_width with width="stretch".
STRETCH = {"width": "stretch"} if _streamlit_version() >= (1, 50) else {"use_container_width": True}

# ---------- Readable, high-contrast visual theme ----------
THEME_CSS = """
<style>
:root {
    --navy: #17324D;
    --navy-deep: #10263B;
    --teal: #087F75;
    --teal-dark: #06665F;
    --cream: #0B1B2B;
    --ink: #FFFFFF;
    --muted: #FFFFFF;
    --border: #3C5A78;
    --soft-teal: #12404A;
    --good: #3DDC97;
    --good-soft: #14402F;
    --bad: #FF6B5E;
    --bad-soft: #4A1F1F;
    --gold: #F2B84B;
}

html, body, .stApp, button, input, textarea {
    font-family: "Segoe UI", Arial, sans-serif !important;
}
.stApp { background: var(--cream) !important; color: var(--ink); }
[data-testid="stHeader"] { background: rgba(11, 27, 43, 0.98) !important; }

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--navy) 0%, var(--navy-deep) 100%) !important;
    border-right: 2px solid #294760 !important;
}
[data-testid="stSidebar"] * { color: #FFFFFF !important; }
[data-testid="stSidebar"] .stRadio label {
    font-size: 1.05rem !important;
    font-weight: 600 !important;
    padding: 0.28rem 0 !important;
}

h1, h2, h3, h4 { color: #FFFFFF !important; font-weight: 750 !important; }
p, li, label, .stCaption { color: var(--ink) !important; }

/* ---------- Hero ---------- */
.hero {
    background: linear-gradient(120deg, var(--navy) 0%, #1F5A7A 55%, var(--teal) 100%);
    padding: 2rem 2.2rem;
    border-radius: 20px;
    margin: 0.3rem 0 1.5rem 0;
    box-shadow: 0 10px 28px rgba(23, 50, 77, 0.22);
    animation: slideIn 0.55s ease both;
}
.hero h1, .hero h2, .hero p, .hero span { color: #FFFFFF !important; }
.hero h1 { font-size: 2.25rem !important; margin: 0 0 0.45rem 0; }
.hero p { font-size: 1.12rem !important; margin: 0; line-height: 1.6; }

/* ---------- Cards ---------- */
.info-card {
    background: #14304A;
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.25rem;
    min-height: 150px;
    box-shadow: 0 3px 12px rgba(23, 50, 77, 0.06);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.info-card:hover { transform: translateY(-4px); box-shadow: 0 10px 22px rgba(23, 50, 77, 0.14); }
.info-card h3 { margin-top: 0; font-size: 1.2rem; }
.info-card p { color: var(--muted) !important; line-height: 1.55; }

.notice {
    background: var(--soft-teal);
    border-left: 5px solid var(--teal);
    border-radius: 10px;
    padding: 0.9rem 1rem;
    color: #FFFFFF !important;
    margin: 0.7rem 0 1rem 0;
}

/* ---------- Game item cards ---------- */
.item-grid { display: flex; flex-wrap: wrap; gap: 14px; justify-content: center; margin: 1rem 0 1.2rem 0; }
.item-card {
    background: #14304A;
    border: 2px solid var(--border);
    border-radius: 18px;
    padding: 0.9rem 1.1rem;
    min-width: 130px;
    text-align: center;
    box-shadow: 0 4px 14px rgba(23, 50, 77, 0.08);
    animation: popIn 0.45s ease both;
    animation-delay: calc(var(--i, 0) * 80ms);
}
.item-card .emoji { font-size: 2.8rem; line-height: 1.2; }
.item-card .label { font-size: 1.25rem; font-weight: 700; color: #FFFFFF; }
.item-card .sub { font-size: 0.9rem; color: var(--muted); margin-top: 0.15rem; }
.item-card .num { font-size: 0.85rem; font-weight: 700; color: #FFFFFF; }
.item-card.word .label { font-size: 1.9rem; padding: 0.4rem 0.6rem; }
.item-card.ok { border-color: var(--good); background: var(--good-soft); }
.item-card.bad { border-color: var(--bad); background: var(--bad-soft); }
.item-card.locked { opacity: 0.5; filter: grayscale(1); }
.item-card.earned { border-color: var(--gold); }
.digit-card { min-width: 70px; padding: 0.6rem 0.8rem; }
.digit-card .label { font-size: 2rem; }

.big-digits {
    background: #14304A;
    border: 2px solid var(--border);
    border-radius: 20px;
    padding: 1.4rem 1rem;
    text-align: center;
    font-size: 3.4rem;
    font-weight: 800;
    letter-spacing: 0.4em;
    color: #FFFFFF;
    box-shadow: 0 6px 18px rgba(23, 50, 77, 0.1);
    animation: popIn 0.5s ease both;
}

/* ---------- Step indicator ---------- */
.stepper { display: flex; gap: 10px; margin: 0.4rem 0 1rem 0; flex-wrap: wrap; }
.step {
    flex: 1; min-width: 110px; text-align: center; padding: 0.55rem 0.8rem;
    border-radius: 999px; background: #1B3A57; color: var(--muted);
    font-weight: 700; font-size: 0.95rem;
}
.step.active { background: var(--teal); color: #FFFFFF; box-shadow: 0 4px 12px rgba(8, 127, 117, 0.35); }
.step.done { background: var(--soft-teal); color: #FFFFFF; }

/* ---------- Buttons ---------- */
.stButton > button,
[data-testid="stFormSubmitButton"] > button,
[data-testid="stDownloadButton"] > button {
    background: var(--teal) !important;
    color: #FFFFFF !important;
    border: 1px solid var(--teal-dark) !important;
    border-radius: 12px !important;
    min-height: 2.8rem;
    font-weight: 700 !important;
    padding: 0.45rem 1.1rem !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
}
.stButton > button:hover,
[data-testid="stFormSubmitButton"] > button:hover,
[data-testid="stDownloadButton"] > button:hover {
    background: var(--teal-dark) !important;
    color: #FFFFFF !important;
    transform: translateY(-2px);
    box-shadow: 0 6px 14px rgba(8, 127, 117, 0.3);
}
.stButton > button:focus,
[data-testid="stFormSubmitButton"] > button:focus {
    outline: 3px solid var(--gold) !important;
    outline-offset: 2px !important;
}

input, textarea, [data-baseweb="select"] > div {
    background: #0F2438 !important;
    color: var(--ink) !important;
    border-color: #9AAABD !important;
}
input::placeholder, textarea::placeholder { color: #FFFFFF !important; opacity: 0.65 !important; }

[data-testid="stMetric"] {
    background: #14304A;
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 0.9rem;
    box-shadow: 0 2px 8px rgba(23, 50, 77, 0.05);
}
[data-testid="stMetricLabel"], [data-testid="stMetricValue"] { color: #FFFFFF !important; }
[data-testid="stForm"] { background: #14304A; border-radius: 16px; border: 1px solid var(--border); }
[data-testid="stAlert"] * { color: var(--ink) !important; }
hr { border-color: var(--border) !important; }

@keyframes slideIn { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: none; } }
@keyframes popIn { from { opacity: 0; transform: scale(0.85); } to { opacity: 1; transform: scale(1); } }
@media (prefers-reduced-motion: reduce) {
    * { animation: none !important; transition: none !important; }
}
/* ---------- Dark-theme extras: keep every piece of text white ---------- */
.stApp span, .stApp small, .stApp summary, .stApp p, .stApp li, .stApp label,
.stApp h1, .stApp h2, .stApp h3, .stApp h4 { color: #FFFFFF !important; }
[data-testid="stAlert"] {
    background: #14304A !important;
    border: 1px solid var(--border);
    border-radius: 12px;
}
[data-testid="stExpander"] {
    background: #14304A;
    border: 1px solid var(--border);
    border-radius: 12px;
}
[data-baseweb="tab"] { color: #FFFFFF !important; }
[data-baseweb="popover"], [data-baseweb="popover"] *, [data-baseweb="menu"],
ul[role="listbox"], ul[role="listbox"] li {
    background: #14304A !important;
    color: #FFFFFF !important;
}
ul[role="listbox"] li:hover { background: #1F5A7A !important; }
[data-testid="stSlider"] * { color: #FFFFFF !important; }
</style>
"""
st.markdown(THEME_CSS, unsafe_allow_html=True)


# ============================================================
# Users and progress storage (one history file per player)
# ============================================================
USERS_FILE = DATA_DIR / "users.json"
AVATARS = ["🙂", "👵", "👴", "👩", "👨", "🧑", "🌸", "🌻", "🦁", "🐼", "🐯", "⭐"]
MAX_USERS = 12


def write_json_atomic(path, data):
    """Write to a temp file first so a crash can never leave a half-written file."""
    fd, tmp_name = tempfile.mkstemp(dir=DATA_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        os.replace(tmp_name, path)
        return True
    except OSError:
        Path(tmp_name).unlink(missing_ok=True)
        return False


def read_json(path, default):
    try:
        with Path(path).open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return default


def progress_path(uid):
    safe = re.sub(r"[^A-Za-z0-9_-]", "", str(uid))
    return DATA_DIR / f"progress_{safe}.json"


def load_users():
    if not USERS_FILE.exists():
        if PROGRESS_FILE.exists():
            # Upgrade from the single-user version: keep the old history as "Player 1".
            users = [{"id": "main", "name": "Player 1", "avatar": "🙂", "pin_hash": "", "salt": ""}]
            try:
                PROGRESS_FILE.replace(progress_path("main"))
            except OSError:
                pass
            write_json_atomic(USERS_FILE, users)
            return users
        return []
    data = read_json(USERS_FILE, [])
    if not isinstance(data, list):
        return []
    return [u for u in data if isinstance(u, dict) and u.get("id") and u.get("name")]


def hash_pin(pin, salt):
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), 100_000).hex()


def verify_pin(user, pin):
    if not user.get("pin_hash"):
        return True
    return hmac.compare_digest(hash_pin(pin or "", user.get("salt", "")), user["pin_hash"])


def add_user(name, avatar, pin):
    """Create a profile. Returns (user, error_message)."""
    name = " ".join((name or "").split())
    pin = (pin or "").strip()
    users = load_users()
    if not name:
        return None, "Please enter a name."
    if len(name) > 20:
        return None, "Please use a name of 20 characters or fewer."
    if any(u["name"].casefold() == name.casefold() for u in users):
        return None, "That name is already taken. Please choose another."
    if len(users) >= MAX_USERS:
        return None, f"You can have up to {MAX_USERS} profiles."
    if pin and not (pin.isdigit() and len(pin) == 4):
        return None, "A PIN must be exactly 4 digits. Leave it empty for no PIN."
    salt = secrets.token_hex(8) if pin else ""
    user = {
        "id": uuid.uuid4().hex[:8],
        "name": name,
        "avatar": avatar if avatar in AVATARS else AVATARS[0],
        "salt": salt,
        "pin_hash": hash_pin(pin, salt) if pin else "",
    }
    users.append(user)
    if not write_json_atomic(USERS_FILE, users):
        return None, "Sorry, the profile could not be saved."
    return user, ""


def delete_user(uid):
    users = [u for u in load_users() if u["id"] != uid]
    write_json_atomic(USERS_FILE, users)
    progress_path(uid).unlink(missing_ok=True)


def load_progress(uid):
    data = read_json(progress_path(uid), [])
    return data if isinstance(data, list) else []


def save_result(game_name, score, details):
    uid = st.session_state.get("user_id")
    if not uid:
        return
    records = load_progress(uid)
    records.append(
        {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "game": game_name,
            "score": int(score),
            "details": details,
        }
    )
    if not write_json_atomic(progress_path(uid), records):
        st.error("Sorry, your result could not be saved.")


def load_records(uid=None):
    """Load a player's progress and clean it so one bad entry can never break a page."""
    uid = uid or st.session_state.get("user_id")
    cleaned = []
    for r in load_progress(uid):
        if not isinstance(r, dict):
            continue
        try:
            score = max(0, min(100, int(float(r.get("score", 0)))))
        except (TypeError, ValueError):
            continue
        try:
            when = datetime.strptime(str(r.get("date", "")), "%Y-%m-%d %H:%M")
        except ValueError:
            when = None
        cleaned.append(
            {
                "date": str(r.get("date", "")),
                "game": str(r.get("game", "Other")),
                "score": score,
                "details": str(r.get("details", "")),
                "_dt": when,
            }
        )
    return cleaned


# ============================================================
# Stats helpers
# ============================================================
def streaks(records):
    """Return (current streak, longest streak) in consecutive days."""
    days = sorted({r["_dt"].date() for r in records if r["_dt"]})
    if not days:
        return 0, 0
    longest = run = 1
    for prev, cur in zip(days, days[1:]):
        run = run + 1 if (cur - prev).days == 1 else 1
        longest = max(longest, run)
    day_set = set(days)
    d = date.today()
    if d not in day_set:
        d -= timedelta(days=1)  # a streak stays alive until the day is over
    current = 0
    while d in day_set:
        current += 1
        d -= timedelta(days=1)
    return current, longest


def today_count(records):
    return sum(1 for r in records if r["_dt"] and r["_dt"].date() == date.today())


def score_badge(score):
    return "🟢" if score >= 80 else "🟡" if score >= 50 else "🔴"


def earned_badges(records):
    total = len(records)
    best = max((r["score"] for r in records), default=0)
    _, longest = streaks(records)
    games = len({r["game"] for r in records})
    return [
        ("🌱", "First Step", "Complete your first activity", total >= 1),
        ("🔥", "Warming Up", "Complete 5 activities", total >= 5),
        ("🏅", "Sharp Mind", "Score 100% in any activity", best >= 100),
        ("📅", "On a Roll", "Play on 3 days in a row", longest >= 3),
        ("🎯", "All-Rounder", "Try all 3 games", games >= 3),
    ]


# ============================================================
# UI helpers
# ============================================================
def hero(title, subtitle):
    st.markdown(
        f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )


def notice(text):
    st.markdown(f'<div class="notice">{text}</div>', unsafe_allow_html=True)


def stepper(current):
    steps = [("study", "1 · Look"), ("recall", "2 · Recall"), ("done", "3 · Result")]
    order = [key for key, _ in steps]
    parts = []
    for key, label in steps:
        if key == current:
            cls = "step active"
        elif order.index(key) < order.index(current):
            cls = "step done"
        else:
            cls = "step"
        parts.append(f'<div class="{cls}">{label}</div>')
    st.markdown(f'<div class="stepper">{"".join(parts)}</div>', unsafe_allow_html=True)


def card(label, emoji="", sub="", state="", index=0, extra_cls="", num=""):
    cls = " ".join(c for c in ["item-card", state, extra_cls] if c)
    parts = []
    if num:
        parts.append(f'<div class="num">{html.escape(str(num))}</div>')
    if emoji:
        parts.append(f'<div class="emoji">{emoji}</div>')
    parts.append(f'<div class="label">{html.escape(str(label))}</div>')
    if sub:
        parts.append(f'<div class="sub">{html.escape(str(sub))}</div>')
    return f'<div class="{cls}" style="--i:{index}">{"".join(parts)}</div>'


def grid(cards):
    st.markdown(f'<div class="item-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def result_banner(score, detail):
    if score == 100:
        st.success(f"🌟 Perfect! {detail}")
    elif score >= 60:
        st.info(f"👏 Well done! {detail}")
    else:
        st.info(f"💪 Good effort. {detail} Every round is good practice.")


def celebrate_once(g):
    if g.get("score") == 100 and not g.get("celebrated"):
        g["celebrated"] = True
        st.balloons()


def navigate_to(target):
    st.session_state["page"] = target


def surprise_me():
    st.session_state["page"] = random.choice(GAME_PAGES)


# ---------- Per-game state ----------
def game_state(key):
    if key not in st.session_state:
        st.session_state[key] = {"phase": "idle", "round": 0}
    return st.session_state[key]


def new_round(key, **data):
    previous = st.session_state.get(key, {}).get("round", 0)
    st.session_state[key] = {"phase": "study", "round": previous + 1, **data}


def to_phase(key, phase):
    st.session_state[key]["phase"] = phase


def to_idle(key):
    st.session_state[key] = {"phase": "idle", "round": st.session_state[key]["round"]}


# ============================================================
# Game data
# ============================================================
MEMORY_ITEMS = {
    "Apple": "🍎", "Key": "🔑", "Flower": "🌸", "Book": "📖",
    "Cup": "☕", "Bell": "🔔", "Tree": "🌳", "Fish": "🐟",
    "Clock": "⏰", "Ball": "⚽", "Umbrella": "☂️", "Moon": "🌙",
}

WORD_BANK = {
    "Nature": ["Garden", "Sunshine", "River", "Mountain", "Rainbow", "Forest", "Ocean", "Meadow", "Butterfly", "Waterfall"],
    "Home": ["Lantern", "Window", "Blanket", "Kitchen", "Cushion", "Doorbell", "Teapot", "Curtain", "Staircase", "Lamp"],
    "Food": ["Mango", "Chapati", "Coconut", "Banana", "Biscuit", "Pickle", "Jaggery", "Lemon", "Cardamom", "Porridge"],
}


def match_words(targets, answers):
    """Return the targets that were recalled. Small spelling slips are accepted."""
    remaining = [a.strip().casefold() for a in answers if a and a.strip()]
    hits = []
    for target in targets:
        best, best_ratio = None, 0.0
        for answer in remaining:
            ratio = SequenceMatcher(None, target.casefold(), answer).ratio()
            if ratio > best_ratio:
                best, best_ratio = answer, ratio
        if best is not None and best_ratio >= 0.84:
            remaining.remove(best)
            hits.append(target)
    return hits


# ---------- Round starters ----------
def start_memory(level):
    new_round("memory", level=level, sequence=random.sample(list(MEMORY_ITEMS), LEVELS[level]))


def start_numbers(level, backwards):
    seq = [str(random.randint(0, 9)) for _ in range(LEVELS[level])]
    new_round("numbers", level=level, backwards=backwards, sequence=seq)


def start_words(count, theme):
    pool = [w for words in WORD_BANK.values() for w in words] if theme == "Mixed" else WORD_BANK[theme]
    new_round("words", count=count, theme=theme, sequence=random.sample(pool, count))


# ============================================================
# Sidebar
# ============================================================
RESET_KEYS = ("memory", "numbers", "words", "pending_user", "confirm_clear", "confirm_delete_user", "delete_pin")


def login(uid):
    for key in RESET_KEYS:
        st.session_state.pop(key, None)
    st.session_state["user_id"] = uid
    st.session_state["page"] = "Home"


def logout():
    for key in RESET_KEYS:
        st.session_state.pop(key, None)
    st.session_state.pop("user_id", None)
    st.session_state["page"] = "Home"


def delete_profile(uid):
    delete_user(uid)
    logout()


def pick_user(uid):
    chosen = next((u for u in load_users() if u["id"] == uid), None)
    if chosen and chosen.get("pin_hash"):
        st.session_state["pending_user"] = uid
    elif chosen:
        login(uid)


def current_user():
    uid = st.session_state.get("user_id")
    if not uid:
        return None
    found = next((u for u in load_users() if u["id"] == uid), None)
    if found is None:
        st.session_state.pop("user_id", None)
    return found


def login_screen():
    hero("Welcome to MindMitra 👋", "Who is playing today? Choose your profile, or create a new one.")
    users = load_users()

    pending = st.session_state.get("pending_user")
    pending_user = next((u for u in users if u["id"] == pending), None)
    if pending_user:
        st.markdown(f"### 🔒 Hello {html.escape(pending_user['name'])}, please enter your PIN", unsafe_allow_html=True)
        with st.form("pin_form", clear_on_submit=True):
            pin = st.text_input("4-digit PIN", type="password", max_chars=4)
            col_ok, col_cancel = st.columns(2)
            unlock = col_ok.form_submit_button("Unlock", **STRETCH)
            cancel = col_cancel.form_submit_button("Back", **STRETCH)
        if unlock:
            if verify_pin(pending_user, pin):
                login(pending_user["id"])
                st.rerun()
            else:
                st.error("That PIN is not correct. Please try again.")
        if cancel:
            st.session_state.pop("pending_user", None)
            st.rerun()
        return

    if users:
        st.subheader("Choose your profile")
        per_row = min(len(users), 4)
        for start in range(0, len(users), per_row):
            for col, u in zip(st.columns(per_row), users[start:start + per_row]):
                with col:
                    st.markdown(
                        card(u["name"], u["avatar"], sub="🔒 PIN protected" if u.get("pin_hash") else "", index=start),
                        unsafe_allow_html=True,
                    )
                    st.button("Play as " + u["name"], key=f"pick_{u['id']}", on_click=pick_user, args=(u["id"],), **STRETCH)

    st.markdown("---")
    with st.expander("➕ Create a new profile", expanded=True):
        with st.form("new_profile_form"):
            name = st.text_input("Your name", max_chars=20, placeholder="For example: Asha")
            avatar = st.radio("Pick a picture", AVATARS, horizontal=True)
            pin = st.text_input(
                "Optional 4-digit PIN (keeps your profile private)", type="password", max_chars=4
            )
            create = st.form_submit_button("Create profile", **STRETCH)
        if create:
            new_user, error = add_user(name, avatar, pin)
            if error:
                st.error(error)
            else:
                login(new_user["id"])
                st.rerun()
    notice("Each person has their own scores, streaks and badges. A PIN is optional and is a simple privacy lock, not strong security.")


# ---------- Who is playing? ----------
user = current_user()
if user is None:
    login_screen()
    st.stop()

USER_ID = user["id"]
records = load_records(USER_ID)
current_streak, longest_streak = streaks(records)

with st.sidebar:
    st.markdown("# 🧠 MindMitra")
    st.markdown(f'<h3>{user["avatar"]} {html.escape(user["name"])}</h3>', unsafe_allow_html=True)
    st.button("🔄 Switch user", on_click=logout, **STRETCH)
    st.markdown("### Cognitive Wellness")
    st.markdown("---")
    st.markdown("### MENU")
    page = st.radio("Choose a page", PAGES, label_visibility="collapsed", key="page")
    st.markdown("---")
    st.markdown("### 🎯 Today's goal")
    goal = st.slider("Activities per day", 1, 10, 3, key="daily_goal")
    done_today = today_count(records)
    st.progress(min(done_today / goal, 1.0), text=f"{done_today} of {goal} done today")
    if done_today >= goal:
        st.markdown("🎉 **Goal reached! Well done.**")
    st.markdown(f"🔥 **{current_streak}-day streak**")
    st.markdown("---")
    big_text = st.toggle("Larger text", key="big_text", help="Makes text and buttons bigger.")
    st.markdown("---")
    st.markdown("### 🌱 Our Mission")
    st.markdown("Making enjoyable brain activities accessible, encouraging and easy to use.")
    st.caption("MindMitra • Cognitive engagement")

if big_text:
    st.markdown(
        "<style>.stMarkdown p, .stMarkdown li, label, .stTextInput input, "
        ".stButton button, [data-testid='stFormSubmitButton'] button "
        "{ font-size: 1.25rem !important; }</style>",
        unsafe_allow_html=True,
    )


# ============================================================
# Home
# ============================================================
if page == "Home":
    greeting = "Hello"
    hero(
        f"{greeting}, {html.escape(user['name'])}! 👋",
        "Your friendly space for memory activities, number challenges, word games "
        "and everyday cognitive engagement.",
    )

    st.subheader("What would you like to do today?")
    st.write("Choose an activity below. You can play at your own pace.")

    cards = [
        ("🧩 Memory Games", "Study a set of pictures, then recall them in order. Practise attention and recall.", "Memory Games"),
        ("🔢 Number Games", "Remember a number sequence, forwards or even backwards, and enter it.", "Number Games"),
        ("🔤 Word Games", "Look at a few words, then type the ones you remember.", "Word Games"),
    ]
    for col, (title, text, target) in zip(st.columns(3), cards):
        with col:
            st.markdown(
                f'<div class="info-card"><h3>{title}</h3><p>{text}</p></div>',
                unsafe_allow_html=True,
            )
            st.button(f"Open {title[2:]}", key=f"open_{target}", on_click=navigate_to, args=(target,), **STRETCH)

    st.button("🎲 Surprise me with a game", on_click=surprise_me)

    st.markdown("---")
    st.subheader("Your activity at a glance")
    total = len(records)
    average = round(sum(r["score"] for r in records) / total, 1) if total else 0
    a, b, c, d = st.columns(4)
    a.metric("Activities completed", total)
    b.metric("Average score", f"{average}%")
    c.metric("Current streak 🔥", f"{current_streak} days")
    d.metric("Today", f"{done_today} / {goal}")
    notice(
        "💡 Tip: A calm space, good lighting and a comfortable pace can make activities "
        "more enjoyable. Take a break whenever you need one."
    )


# ============================================================
# Memory game
# ============================================================
elif page == "Memory Games":
    hero("🧩 Memory Match", "Study the pictures, then recall them in order. There is no timer pressure.")
    g = game_state("memory")

    if g["phase"] == "idle":
        st.write("**How to play:** Look at the pictures, press the button to hide them, then pick them in the same order.")
        level = st.select_slider("Difficulty", options=list(LEVELS), key="memory_level")
        st.caption(f"{LEVELS[level]} items to remember.")
        st.button("▶ Start a new memory round", on_click=start_memory, args=(level,))
        notice("Press <b>Start</b> when you are ready. Take all the time you need to study.")

    elif g["phase"] == "study":
        stepper("study")
        st.info("Take a moment to remember these items, in this order:")
        grid([card(item, MEMORY_ITEMS[item], index=i, num=f"#{i + 1}") for i, item in enumerate(g["sequence"])])
        st.write("When you feel ready, hide the items and try to recall them.")
        st.button("✅ I'm ready, hide them", on_click=to_phase, args=("memory", "recall"))

    elif g["phase"] == "recall":
        stepper("recall")
        n = len(g["sequence"])
        with st.form(f"memory_form_{g['round']}"):
            st.write("Choose the items in the order you saw them.")
            cols = st.columns(min(n, 4))
            answers = []
            for i in range(n):
                with cols[i % len(cols)]:
                    answers.append(
                        st.selectbox(
                            f"Item {i + 1}",
                            list(MEMORY_ITEMS),
                            index=None,
                            placeholder="Choose…",
                            format_func=lambda name: f"{MEMORY_ITEMS[name]} {name}",
                            key=f"mem_{g['round']}_{i}",
                        )
                    )
            submitted = st.form_submit_button("Check my answers", **STRETCH)
        if submitted:
            correct = sum(a == s for a, s in zip(answers, g["sequence"]))
            score = round(correct / n * 100)
            g.update(phase="done", answers=answers, correct=correct, score=score)
            save_result("Memory Match", score, f"{correct} of {n} in the right place ({g['level']})")
            st.rerun()

    else:  # done
        stepper("done")
        n = len(g["sequence"])
        result_banner(g["score"], f"You placed {g['correct']} of {n} items correctly. Score: {g['score']}%.")
        celebrate_once(g)
        cells = []
        for i, (answer, expected) in enumerate(zip(g["answers"], g["sequence"])):
            ok = answer == expected
            sub = "✓ Correct" if ok else f"You chose: {answer or 'nothing'}"
            cells.append(card(expected, MEMORY_ITEMS[expected], sub=sub, state="ok" if ok else "bad", index=i, num=f"#{i + 1}"))
        grid(cells)
        c1, c2 = st.columns(2)
        c1.button("🔁 Play again", on_click=start_memory, args=(g["level"],), **STRETCH)
        c2.button("⚙ Change difficulty", on_click=to_idle, args=("memory",), **STRETCH)


# ============================================================
# Number game
# ============================================================
elif page == "Number Games":
    hero("🔢 Number Recall", "Look at a short number sequence, then enter it from memory.")
    g = game_state("numbers")

    if g["phase"] == "idle":
        st.write("Choose a difficulty level. You can practise as many times as you like.")
        level = st.select_slider("Difficulty", options=list(LEVELS), key="number_level")
        backwards = st.checkbox("🔄 Backwards mode (enter the digits in reverse)", key="number_backwards")
        st.caption(f"{LEVELS[level]} digits to remember.")
        st.button("▶ Generate number sequence", on_click=start_numbers, args=(level, backwards))
        notice("Start with <b>Easy</b> if this is your first round.")

    elif g["phase"] == "study":
        stepper("study")
        st.info("Remember this sequence:" + (" (you will type it backwards)" if g["backwards"] else ""))
        st.markdown(f'<div class="big-digits">{" ".join(g["sequence"])}</div>', unsafe_allow_html=True)
        st.write("")
        st.button("✅ I'm ready, hide the numbers", on_click=to_phase, args=("numbers", "recall"))

    elif g["phase"] == "recall":
        stepper("recall")
        n = len(g["sequence"])
        with st.form(f"number_form_{g['round']}"):
            st.write(
                f"Type the {n} digits "
                + ("in **reverse** order." if g["backwards"] else "in the same order.")
            )
            typed = st.text_input("Your answer", key=f"num_{g['round']}", placeholder="Enter the digits here")
            submitted = st.form_submit_button("Check number sequence", **STRETCH)
        if submitted:
            expected = g["sequence"][::-1] if g["backwards"] else g["sequence"]
            digits = [ch for ch in typed if ch.isdigit()]
            correct = sum(1 for i, e in enumerate(expected) if i < len(digits) and digits[i] == e)
            score = round(correct / n * 100)
            g.update(phase="done", expected=expected, typed=digits, correct=correct, score=score)
            mode = "backwards" if g["backwards"] else "forwards"
            save_result("Number Recall", score, f"{correct} of {n} digits correct ({g['level']}, {mode})")
            st.rerun()

    else:  # done
        stepper("done")
        n = len(g["sequence"])
        result_banner(g["score"], f"You got {g['correct']} of {n} digits right. Score: {g['score']}%.")
        celebrate_once(g)
        label = "Correct answer (reversed)" if g["backwards"] else "Correct answer"
        st.write(f"**{label}:**")
        cells = []
        for i, expected in enumerate(g["expected"]):
            typed_digit = g["typed"][i] if i < len(g["typed"]) else ""
            ok = typed_digit == expected
            sub = "✓" if ok else f"You: {typed_digit or '–'}"
            cells.append(card(expected, sub=sub, state="ok" if ok else "bad", index=i, extra_cls="digit-card"))
        grid(cells)
        c1, c2 = st.columns(2)
        c1.button("🔁 Try another sequence", on_click=start_numbers, args=(g["level"], g["backwards"]), **STRETCH)
        c2.button("⚙ Change settings", on_click=to_idle, args=("numbers",), **STRETCH)


# ============================================================
# Word game
# ============================================================
elif page == "Word Games":
    hero("🔤 Word Recall", "Read the words carefully, then type the ones you remember.")
    g = game_state("words")

    if g["phase"] == "idle":
        st.write("Choose a theme and how many words to remember. Order does not matter, and small spelling slips are fine.")
        theme = st.radio("Theme", ["Mixed", *WORD_BANK], horizontal=True, key="word_theme")
        count = st.slider("Number of words", 1, 6, 3, key="word_count")
        st.button("▶ Show me the words", on_click=start_words, args=(count, theme))
        notice("Press <b>Show me the words</b> to begin.")

    elif g["phase"] == "study":
        stepper("study")
        st.info("Read these words and try to remember them:")
        grid([card(word, index=i, extra_cls="word") for i, word in enumerate(g["sequence"])])
        st.button("✅ I'm ready, hide the words", on_click=to_phase, args=("words", "recall"))

    elif g["phase"] == "recall":
        stepper("recall")
        n = len(g["sequence"])
        with st.form(f"word_form_{g['round']}"):
            st.write(f"Type the {n} word{'s' if n > 1 else ''} you remember, in any order.")
            answers = [
                st.text_input(f"Word {i + 1}", key=f"word_{g['round']}_{i}", placeholder="Your answer")
                for i in range(n)
            ]
            submitted = st.form_submit_button("Check my words", **STRETCH)
        if submitted:
            hits = match_words(g["sequence"], answers)
            score = round(len(hits) / n * 100)
            g.update(phase="done", hits=hits, score=score)
            save_result("Word Recall", score, f"{len(hits)} of {n} words recalled ({g['theme']})")
            st.rerun()

    else:  # done
        stepper("done")
        n = len(g["sequence"])
        result_banner(g["score"], f"You remembered {len(g['hits'])} of {n} words. Score: {g['score']}%.")
        celebrate_once(g)
        cells = []
        for i, word in enumerate(g["sequence"]):
            ok = word in g["hits"]
            cells.append(card(word, sub="✓ Remembered" if ok else "Missed this time", state="ok" if ok else "bad", index=i, extra_cls="word"))
        grid(cells)
        c1, c2 = st.columns(2)
        c1.button("🔁 Try more words", on_click=start_words, args=(g["count"], g["theme"]), **STRETCH)
        c2.button("⚙ Change settings", on_click=to_idle, args=("words",), **STRETCH)


# ============================================================
# Progress
# ============================================================
elif page == "My Progress":
    hero("📊 My Progress", "Review completed activities and see how your practice is going.")
    if not records:
        st.info("No activities recorded yet. Complete a game to see your progress here.")
        st.button("Play a game now", on_click=surprise_me)
    else:
        total = len(records)
        scores = [r["score"] for r in records]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Activities completed", total)
        c2.metric("Average score", f"{sum(scores) / total:.1f}%")
        c3.metric("Best score", f"{max(scores)}%")
        c4.metric("Streak 🔥", f"{current_streak} days", help=f"Longest streak: {longest_streak} days")

        latest = records[-1]
        st.progress(latest["score"] / 100, text=f"Latest: {latest['game']} {score_badge(latest['score'])} {latest['score']}%")

        tab_trend, tab_games, tab_history, tab_badges = st.tabs(
            ["📈 Trend", "🎮 By activity", "🗂 History", "🏆 Badges"]
        )
        with tab_trend:
            recent = scores[-30:]
            trend = pd.DataFrame({"Score (%)": recent}, index=range(1, len(recent) + 1))
            trend.index.name = "Session"
            st.line_chart(trend, color=TEAL, height=280)
            st.caption(f"Your last {len(recent)} sessions.")

        with tab_games:
            df = pd.DataFrame({"Activity": [r["game"] for r in records], "Score": scores})
            left, right = st.columns(2)
            with left:
                st.markdown("**Times played**")
                st.bar_chart(df["Activity"].value_counts(), color=TEAL)
            with right:
                st.markdown("**Average score (%)**")
                st.bar_chart(df.groupby("Activity")["Score"].mean().round(0), color="#17324D")

        with tab_history:
            choice = st.selectbox("Filter by activity", ["All"] + sorted({r["game"] for r in records}))
            rows = [r for r in reversed(records) if choice == "All" or r["game"] == choice][:50]
            table = pd.DataFrame(
                [{"Date": r["date"], "Activity": r["game"], "Score": r["score"], "Details": r["details"]} for r in rows]
            )
            st.dataframe(
                table,
                hide_index=True,
                column_config={
                    "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d%%")
                },
                **STRETCH,
            )

        with tab_badges:
            badges = earned_badges(records)
            grid(
                [
                    card(name, emoji, sub=desc, state="earned" if got else "locked", index=i)
                    for i, (emoji, name, desc, got) in enumerate(badges)
                ]
            )
            st.caption(f"{sum(1 for b in badges if b[3])} of {len(badges)} badges earned.")

        with st.expander("⚠️ Clear saved progress"):
            st.write("This permanently deletes all saved activity history.")
            if st.checkbox("Yes, I want to delete my history", key="confirm_clear"):
                if st.button("Delete everything"):
                    progress_path(USER_ID).unlink(missing_ok=True)
                    st.session_state["confirm_clear"] = False
                    st.rerun()

    with st.expander("👤 Profile settings"):
        st.write(f"You are signed in as **{user['name']}**.")
        if st.checkbox("I want to delete this profile and all its history", key="confirm_delete_user"):
            pin_ok = True
            if user.get("pin_hash"):
                typed_pin = st.text_input("Enter your PIN to confirm", type="password", max_chars=4, key="delete_pin")
                pin_ok = verify_pin(user, typed_pin)
            st.button("Delete profile permanently", disabled=not pin_ok, on_click=delete_profile, args=(USER_ID,))


# ============================================================
# Caregiver dashboard
# ============================================================
elif page == "Caregiver Dashboard":
    hero("🤝 Caregiver Dashboard", "A simple overview of recorded game activity to support conversations and encouragement.")
    all_users = load_users()
    labels = {u["id"]: f"{u['avatar']} {u['name']}" for u in all_users}
    view_ids = ["all"] + [u["id"] for u in all_users]
    pick = st.selectbox(
        "Whose activity would you like to see?",
        view_ids,
        format_func=lambda x: "👥 All players" if x == "all" else labels[x],
        key="caregiver_view",
    )
    shown = all_users if pick == "all" else [u for u in all_users if u["id"] == pick]

    rows = []
    for u in shown:
        for r in load_records(u["id"]):
            rows.append({**r, "Player": u["name"]})
    rows.sort(key=lambda r: r["_dt"] or datetime.min)

    if rows:
        df = pd.DataFrame(
            [
                {"Player": r["Player"], "Date": r["date"], "Activity": r["game"], "Score": r["score"], "Details": r["details"]}
                for r in rows
            ]
        )
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total completed games", len(rows))
        c2.metric("Average score", f"{df['Score'].mean():.1f}%")
        c3.metric("Different activities", df["Activity"].nunique())
        if pick == "all":
            c4.metric("Players with activity", df["Player"].nunique())
        else:
            c4.metric("Days active in a row", streaks(rows)[0])

        left, right = st.columns(2)
        with left:
            st.subheader("Last 7 days")
            days = [date.today() - timedelta(days=i) for i in range(6, -1, -1)]
            per_day = Counter(r["_dt"].date() for r in rows if r["_dt"])
            week = pd.DataFrame({"Activities": [per_day.get(d, 0) for d in days]}, index=pd.to_datetime(days))
            st.bar_chart(week, color=TEAL)
        with right:
            st.subheader("Activities completed")
            st.bar_chart(df["Activity"].value_counts(), color="#17324D")

        if pick == "all" and df["Player"].nunique() > 1:
            st.subheader("Players compared")
            left, right = st.columns(2)
            with left:
                st.markdown("**Games played**")
                st.bar_chart(df["Player"].value_counts(), color=TEAL)
            with right:
                st.markdown("**Average score (%)**")
                st.bar_chart(df.groupby("Player")["Score"].mean().round(0), color="#17324D")

        st.subheader("Latest recorded sessions")
        st.dataframe(
            df.iloc[::-1].head(10),
            hide_index=True,
            column_config={
                "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d%%")
            },
            **STRETCH,
        )
        st.download_button(
            "⬇ Download activity (CSV)",
            data=df.to_csv(index=False),
            file_name="mindmitra_activity.csv",
            mime="text/csv",
        )
    else:
        st.info("There is no recorded activity yet. Completed games will appear here.")
    notice(
        "This dashboard shows game activity only. Scores are not a medical assessment "
        "and should not be used to diagnose or monitor dementia."
    )


# ============================================================
# About
# ============================================================
elif page == "About":
    hero("About MindMitra", "A friendly cognitive engagement platform designed around simple, accessible activities.")
    st.subheader("What MindMitra offers")
    st.write(
        "- Memory recall activities with pictures\n"
        "- Number sequence challenges, forwards or backwards\n"
        "- Word recall activities with themes\n"
        "- Separate profiles for each person, with an optional PIN\n"
        "- Daily goals, streaks and friendly badges\n"
        "- A caregiver-facing activity overview"
    )
    st.subheader("Designed with accessibility in mind")
    st.write(
        "MindMitra uses large headings, high-contrast colours, clear buttons, a larger-text option "
        "and simple instructions. Activities can be completed at an individual pace, with no timers."
    )
    with st.expander("How does each game work?"):
        st.write(
            "1. **Look**: study the items for as long as you like.\n"
            "2. **Recall**: press the button to hide them and enter what you remember.\n"
            "3. **Result**: see what you got right and play again."
        )
    with st.expander("Where is my data stored?"):
        st.write("Each profile\'s results are saved in their own file inside the `data` folder on the computer running this app. Nothing is sent online.")
    st.warning(
        "MindMitra is an educational and engagement tool. It is not a medical device, "
        "does not diagnose dementia and does not replace professional care."
    )

st.markdown("---")
st.caption("© MindMitra | AI-Assisted Cognitive Gaming Platform")
# 