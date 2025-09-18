import random
from collections import Counter
from pathlib import Path

import streamlit as st
from PIL import Image

# -------------------- App setup --------------------
st.set_page_config(page_title="Gui Gui Math Trainer", page_icon="🧮", layout="centered")

# -------------------- Assets & Blocks --------------------
ASSET_DIR = Path("assets/blocks")

# Available blocks (put PNGs in assets/blocks/). Weights make rare blocks rarer.
BLOCKS = [
    {"name": "Grass",        "emoji": "🟩", "file": "grass.png",         "weight": 8},
    {"name": "Dirt",         "emoji": "🟫", "file": "dirt.png",          "weight": 8},
    {"name": "Stone",        "emoji": "🪨", "file": "stone.png",         "weight": 8},
    {"name": "Oak Planks",   "emoji": "🪵", "file": "oak_planks.png",    "weight": 6},
    {"name": "Brick",        "emoji": "🧱", "file": "brick.png",         "weight": 5},
    {"name": "Sand",         "emoji": "🟨", "file": "sand.png",          "weight": 6},
    {"name": "Water",        "emoji": "🌊", "file": "water.png",         "weight": 5},
    {"name": "Coal Ore",     "emoji": "⚫", "file": "coal_ore.png",      "weight": 4},
    {"name": "Iron Ore",     "emoji": "⚙️", "file": "iron_ore.png",      "weight": 3},
    {"name": "Gold Ore",     "emoji": "⭐", "file": "gold_ore.png",      "weight": 2},
    {"name": "Lapis Ore",    "emoji": "🔷", "file": "lapis_ore.png",     "weight": 2},
    {"name": "Redstone Ore", "emoji": "🔴", "file": "redstone_ore.png",  "weight": 2},
    {"name": "Diamond Ore",  "emoji": "💎", "file": "diamond_ore.png",   "weight": 1},
    {"name": "Obsidian",     "emoji": "⬛", "file": "obsidian.png",      "weight": 1},
    {"name": "TNT",          "emoji": "🧨", "file": "tnt.png",           "weight": 1},
]

@st.cache_data(show_spinner=False)
def load_block_images():
    imgs = {}
    for b in BLOCKS:
        path = ASSET_DIR / b["file"]
        if path.exists():
            try:
                img = Image.open(path).convert("RGBA")
                imgs[b["name"]] = img
            except Exception:
                imgs[b["name"]] = None
        else:
            imgs[b["name"]] = None
    return imgs

BLOCK_IMAGES = load_block_images()

def get_block_visual(name):
    """Return (image or None, emoji) for a block name."""
    img = BLOCK_IMAGES.get(name)
    emoji = next(b["emoji"] for b in BLOCKS if b["name"] == name)
    return img, emoji

# -------------------- Math generators --------------------
def gen_add(min_n, max_n):
    a = random.randint(min_n, max_n)
    b = random.randint(min_n, max_n)
    return a, b, "+", a + b

def gen_sub(min_n, max_n):
    a = random.randint(min_n, max_n)
    b = random.randint(min_n, max_n)
    if b > a:
        a, b = b, a
    return a, b, "−", a - b

def gen_mul(min_n, max_n):
    a = random.randint(min_n, max_n)
    b = random.randint(min_n, max_n)
    return a, b, "×", a * b

def gen_div(min_n, max_n):
    b = random.randint(max(min_n, 1), max_n)  # avoid zero divisor
    result = random.randint(min_n, max_n)
    a = b * result
    return a, b, "÷", result

def generate_questions(n, ops, min_n, max_n):
    qs = []
    for _ in range(n):
        op = random.choice(ops)
        if op == "+":
            a, b, sym, ans = gen_add(min_n, max_n)
        elif op == "−":
            a, b, sym, ans = gen_sub(min_n, max_n)
        elif op == "×":
            a, b, sym, ans = gen_mul(min_n, max_n)
        else:
            a, b, sym, ans = gen_div(min_n, max_n)
        qs.append({"a": a, "b": b, "op": sym, "answer": ans, "text": f"{a} {sym} {b} = ?"})
    return qs

# -------------------- Game state helpers --------------------
def reset_game(num_q=10, min_n=0, max_n=12, ops=None):
    if ops is None:
        ops = ["+", "−", "×", "÷"]
    st.session_state.questions = generate_questions(num_q, ops, min_n, max_n)
    st.session_state.idx = 0
    st.session_state.attempts_left = 3
    st.session_state.score = 0
    st.session_state.finished = False
    st.session_state.feedback = ""
    st.session_state.question_done = False
    st.session_state.last_correct = None
    st.session_state.user_answer = None
    st.session_state.inventory = []  # collected blocks

def award_block():
    names = [b["name"] for b in BLOCKS]
    weights = [b["weight"] for b in BLOCKS]
    choice = random.choices(names, weights=weights, k=1)[0]
    st.session_state.inventory.append(choice)
    return choice

def inventory_counts():
    # Robust against missing key
    return Counter(st.session_state.get("inventory", []))

def inventory_gallery():
    counts = inventory_counts()
    if not counts:
        st.caption("No blocks yet — answer correctly to collect some! ⛏️")
        return
    cols = st.columns(5)
    i = 0
    for name, cnt in sorted(counts.items()):
        img, emoji = get_block_visual(name)
        with cols[i % len(cols)]:
            if img is not None:
                st.image(img, use_container_width=True)
            else:
                st.markdown(
                    "<div style='font-size:48px;text-align:center'>{}</div>".format(emoji),
                    unsafe_allow_html=True,
                )
            st.markdown(
                "<div style='text-align:center'><b>{}</b><br/>× {}</div>".format(name, cnt),
                unsafe_allow_html=True,
            )
        i += 1

def inventory_quick_row():
    counts = inventory_counts()
    if not counts:
        st.caption("No blocks yet.")
        return
    items = []
    for name, cnt in sorted(counts.items()):
        _, emoji = get_block_visual(name)
        items.append(f"{emoji}×{cnt}")
    st.write(" ".join(items))

# -------------------- Initialize state BEFORE sidebar --------------------
if "questions" not in st.session_state:
    reset_game()

# -------------------- Sidebar --------------------
with st.sidebar:
    st.header("⚙️ Settings")
    num_q = st.slider("Number of questions", 5, 20, 10, 1)
    max_n = st.slider("Largest number", 5, 20, 12, 1)
    include_add = st.checkbox("Addition (+)", True)
    include_sub = st.checkbox("Subtraction (−)", True)
    include_mul = st.checkbox("Multiplication (×)", True)
    include_div = st.checkbox("Division (÷)", True)

    chosen_ops = []
    if include_add:
        chosen_ops.append("+")
    if include_sub:
        chosen_ops.append("−")
    if include_mul:
        chosen_ops.append("×")
    if include_div:
        chosen_ops.append("÷")

    if not chosen_ops:
        st.warning("Select at least one operation to include.")

    if st.button("🔄 Start new game", type="primary", use_container_width=True, disabled=not chosen_ops):
        reset_game(num_q=num_q, min_n=0, max_n=max_n, ops=chosen_ops)

    st.divider()
    st.subheader("🎒 Inventory")
    inventory_gallery()

# -------------------- Header --------------------
st.title("🧮 Gui Gui  Kids Math Trainer")
st.caption(
    "You have **3 attempts** per question. Answer correctly to collect a **Minecraft-style block** image! "
    "Default: **10 questions** (change in the sidebar)."
)

# -------------------- Finished screen --------------------
if st.session_state.finished:
    total = len(st.session_state.questions)
    st.success(f"All done! Score: **{st.session_state.score} / {total}** 🎉")
    percent = int(round(100 * st.session_state.score / total))
    st.progress(percent / 100)
    if percent == 100:
        st.balloons()

    st.divider()
    st.subheader("🎒 Your Block Collection")
    inventory_gallery()

    with st.expander("See all questions and answers"):
        rows = []
        for q in st.session_state.questions:
            rows.append(f"{q['text'].replace('= ?', '= ' + str(q['answer']))}")
        st.markdown("\n".join([f"- {r}" for r in rows]))

    st.button("Play again", on_click=reset_game, type="primary")
    st.stop()

# -------------------- Current question --------------------
idx = st.session_state.idx
total = len(st.session_state.questions)
q = st.session_state.questions[idx]
st.write(f"**Question {idx + 1} of {total}**")
st.progress(idx / total)

with st.expander("Quick view: your blocks so far", expanded=False):
    inventory_quick_row()

st.markdown(f"### {q['text']}")
st.caption(f"Attempts left: **{st.session_state.attempts_left}**")

# -------------------- Answer form --------------------
with st.form("answer_form", clear_on_submit=False):
    ans = st.number_input(
        "Your answer",
        value=st.session_state.user_answer if st.session_state.user_answer is not None else 0,
        step=1,
        format="%d",
    )
    submitted = st.form_submit_button("Check")

if submitted and not st.session_state.question_done:
    st.session_state.user_answer = int(ans)
    if int(ans) == q["answer"]:
        st.session_state.score += 1
        won = award_block()
        img, emoji = get_block_visual(won)
        if img is not None:
            st.toast(f"You earned a {won} block!", icon="✅")
            st.image(img, caption=f"You earned: {won}", use_container_width=True)
        else:
            st.toast(f"You earned a {emoji} {won} block!", icon="✅")
        st.session_state.feedback = f"✅ Correct! You got a **{won}** block!"
        st.session_state.question_done = True
        st.session_state.last_correct = True
    else:
        st.session_state.attempts_left -= 1
        if st.session_state.attempts_left > 0:
            st.session_state.feedback = (
                f"❌ Not quite. Try again! Attempts left: {st.session_state.attempts_left}"
            )
            st.session_state.last_correct = False
        else:
            st.session_state.feedback = (
                f"❌ Out of attempts. The correct answer was **{q['answer']}**."
            )
            st.session_state.question_done = True
            st.session_state.last_correct = False

# -------------------- Feedback & navigation --------------------
if st.session_state.feedback:
    if st.session_state.question_done:
        st.info(st.session_state.feedback)
    else:
        st.warning(st.session_state.feedback)

col1, col2 = st.columns(2)
with col1:
    if st.session_state.question_done:
        if st.button("➡️ Next question", type="primary", use_container_width=True):
            st.session_state.idx += 1
            st.session_state.attempts_left = 3
            st.session_state.feedback = ""
            st.session_state.question_done = False
            st.session_state.last_correct = None
            st.session_state.user_answer = None
            if st.session_state.idx >= len(st.session_state.questions):
                st.session_state.finished = True
            st.rerun()
with col2:
    if st.button("🔁 Restart game", use_container_width=True):
        reset_game()
        st.rerun()

st.write("")
st.caption(
    "Tip: Put PNGs in **assets/blocks/** using the listed filenames. Missing images will show emojis instead."
)
