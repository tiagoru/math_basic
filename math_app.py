import random
import json
from collections import Counter
from pathlib import Path

import streamlit as st
from PIL import Image

# -------------------- App setup --------------------
st.set_page_config(page_title="Gui Gui Math Trainer + Builder", page_icon="🧮", layout="centered")

# -------------------- Assets & Blocks --------------------
ASSET_DIR = Path("assets/blocks")

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
    st.session_state.inventory = st.session_state.get("inventory", [])  # keep previous blocks unless starting new run
    st.session_state.inventory = [] if st.session_state.get("force_new_inventory") else st.session_state.inventory

def award_block():
    names = [b["name"] for b in BLOCKS]
    weights = [b["weight"] for b in BLOCKS]
    choice = random.choices(names, weights=weights, k=1)[0]
    st.session_state.inventory.append(choice)
    return choice

def inventory_counts():
    return Counter(st.session_state.get("inventory", []))

# ----- Builder helpers -----
def init_builder(rows=8, cols=12):
    if "builder" not in st.session_state:
        st.session_state.builder = {
            "rows": rows,
            "cols": cols,
            "grid": [[None for _ in range(cols)] for _ in range(rows)],
        }

def builder_used_counts():
    used = Counter()
    b = st.session_state.get("builder")
    if not b:
        return used
    for r in range(b["rows"]):
        for c in range(b["cols"]):
            name = b["grid"][r][c]
            if name:
                used[name] += 1
    return used

def remaining_counts():
    inv = inventory_counts()
    used = builder_used_counts()
    rem = Counter(inv)
    for k, v in used.items():
        rem[k] -= v
    # remove non-positive
    for k in list(rem.keys()):
        if rem[k] <= 0:
            del rem[k]
    return rem

def place_block(r, c, name):
    b = st.session_state.builder
    # refund currently placed block in that cell
    cur = b["grid"][r][c]
    rem = remaining_counts()
    if name is None:
        b["grid"][r][c] = None
        return True
    # only place if we still have remaining of that block or if replacing same type (no net change)
    if rem.get(name, 0) > 0 or cur == name:
        b["grid"][r][c] = name
        return True
    return False

def grid_as_emojis():
    b = st.session_state.builder
    rows = []
    for r in range(b["rows"]):
        row = []
        for c in range(b["cols"]):
            name = b["grid"][r][c]
            if name is None:
                row.append("⬜")
            else:
                _, emoji = get_block_visual(name)
                row.append(emoji)
        rows.append(row)
    return rows

def export_layout():
    b = st.session_state.builder
    return {
        "rows": b["rows"],
        "cols": b["cols"],
        "grid": b["grid"],
    }

def import_layout(data: dict):
    rows = int(data.get("rows", 8))
    cols = int(data.get("cols", 12))
    grid = data.get("grid", [[None]*cols for _ in range(rows)])
    st.session_state.builder = {"rows": rows, "cols": cols, "grid": grid}

# -------------------- Initialize state BEFORE UI --------------------
if "questions" not in st.session_state:
    reset_game()

init_builder()  # ensure builder exists

# -------------------- Tabs --------------------
tab_practice, tab_builder = st.tabs(["🧮 Practice", "🧱 Builder"])

# ==================== PRACTICE TAB ====================
with tab_practice:
    # Sidebar for practice settings
    with st.sidebar:
        st.header("⚙️ Practice Settings")
        num_q = st.slider("Number of questions", 5, 20, 10, 1, key="pq_num_q")
        max_n = st.slider("Largest number", 5, 1000, 12, 1, key="pq_max_n")
        include_add = st.checkbox("Addition (+)", True, key="pq_add")
        include_sub = st.checkbox("Subtraction (−)", True, key="pq_sub")
        include_mul = st.checkbox("Multiplication (×)", True, key="pq_mul")
        include_div = st.checkbox("Division (÷)", True, key="pq_div")

        chosen_ops = []
        if include_add: chosen_ops.append("+")
        if include_sub: chosen_ops.append("−")
        if include_mul: chosen_ops.append("×")
        if include_div: chosen_ops.append("÷")

        if not chosen_ops:
            st.warning("Select at least one operation to include.")

        colA, colB = st.columns(2)
        with colA:
            if st.button("🔄 Start new game", type="primary", use_container_width=True, disabled=not chosen_ops):
                st.session_state.force_new_inventory = False  # keep blocks
                reset_game(num_q=num_q, min_n=0, max_n=max_n, ops=chosen_ops)
                st.rerun()
        with colB:
            if st.button("🧹 New game & clear blocks", use_container_width=True):
                st.session_state.force_new_inventory = True  # reset blocks
                reset_game(num_q=num_q, min_n=0, max_n=max_n, ops=chosen_ops)
                st.rerun()

        st.divider()
        st.subheader("🎒 Inventory (earned blocks)")
        inv = inventory_counts()
        if inv:
            lines = []
            for name, cnt in sorted(inv.items()):
                _, emoji = get_block_visual(name)
                lines.append(f"- {emoji} **{name}** × **{cnt}**")
            st.markdown("\n".join(lines))
        else:
            st.caption("No blocks yet — answer correctly to collect some! ⛏️")

    # Header
    st.title("🧮 Kids Math Trainer")
    st.caption("You have **3 attempts** per question. Answer correctly to collect block rewards. Numbers can go up to **1000** (see sidebar).")

    # Finished screen
    if st.session_state.finished:
        total = len(st.session_state.questions)
        st.success(f"All done! Score: **{st.session_state.score} / {total}** 🎉")
        percent = int(round(100 * st.session_state.score / total))
        st.progress(percent / 100)
        if percent == 100:
            st.balloons()

        with st.expander("See all questions and answers"):
            rows = []
            for q in st.session_state.questions:
                rows.append(f"{q['text'].replace('= ?', '= ' + str(q['answer']))}")
            st.markdown("\n".join([f"- {r}" for r in rows]))

        st.stop()

    # Current question
    idx = st.session_state.idx
    total = len(st.session_state.questions)
    q = st.session_state.questions[idx]
    st.write(f"**Question {idx + 1} of {total}**")
    st.progress(idx / total)

    st.markdown(f"### {q['text']}")
    st.caption(f"Attempts left: **{st.session_state.attempts_left}**")

    # Answer form
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
        if st.button("🔁 Restart practice (keep blocks)", use_container_width=True):
            st.session_state.force_new_inventory = False
            reset_game(num_q=st.session_state.get("pq_num_q", 10),
                       min_n=0,
                       max_n=st.session_state.get("pq_max_n", 12),
                       ops=[o for o in ["+","−","×","÷"]
                            if st.session_state.get("pq_add", True) and o=="+" or
                               st.session_state.get("pq_sub", True) and o=="−" or
                               st.session_state.get("pq_mul", True) and o=="×" or
                               st.session_state.get("pq_div", True) and o=="÷"])
            st.rerun()

# ==================== BUILDER TAB ====================
with tab_builder:
    st.title("🧱 Block Builder (mini Minecraft-like)")
    st.caption("Place blocks on a grid using only what you've earned in Practice. Save or load your world.")

    # Sidebar for builder settings
    with st.sidebar:
        st.header("⚙️ Builder Settings")
        rows = st.slider("Rows", 4, 20, st.session_state.builder["rows"])
        cols = st.slider("Columns", 4, 30, st.session_state.builder["cols"])
        if (rows != st.session_state.builder["rows"]) or (cols != st.session_state.builder["cols"]):
            # Resize grid while keeping existing layout
            old = st.session_state.builder
            new_grid = [[None for _ in range(cols)] for _ in range(rows)]
            for r in range(min(rows, old["rows"])):
                for c in range(min(cols, old["cols"])):
                    new_grid[r][c] = old["grid"][r][c]
            st.session_state.builder = {"rows": rows, "cols": cols, "grid": new_grid}

        st.divider()
        st.subheader("🎒 Blocks Available")
        rem = remaining_counts()
        if rem:
            lines = []
            for name in sorted(rem.keys()):
                _, emoji = get_block_visual(name)
                lines.append(f"- {emoji} **{name}** × **{rem[name]}**")
            st.markdown("\n".join(lines))
        else:
            st.caption("No remaining blocks to place. Earn more in Practice!")

        st.divider()
        # Save layout
        save_data = json.dumps(export_layout(), ensure_ascii=False, indent=2)
        st.download_button("💾 Download world (JSON)", data=save_data, file_name="world.json", mime="application/json")

        # Load layout
        up = st.file_uploader("📤 Load world (JSON)", type=["json"])
        if up is not None:
            try:
                imported = json.loads(up.read().decode("utf-8"))
                import_layout(imported)
                st.success("World loaded!")
            except Exception as e:
                st.error(f"Could not load world: {e}")

        if st.button("🧹 Clear world"):
            r = st.session_state.builder["rows"]
            c = st.session_state.builder["cols"]
            st.session_state.builder["grid"] = [[None for _ in range(c)] for _ in range(r)]

    # Controls
    colL, colR = st.columns([1, 2], vertical_alignment="top")

    with colL:
        st.subheader("Controls")
        # Choose a block to place
        rem = remaining_counts()
        all_names = [b["name"] for b in BLOCKS]
        # Options show only blocks you can place now (remaining>0)
        placeable = [n for n in all_names if rem.get(n, 0) > 0]
        selected_block = st.selectbox("Block to place", placeable, index=0 if placeable else None, placeholder="No blocks available")

        r = st.number_input("Row", min_value=0, max_value=st.session_state.builder["rows"] - 1, step=1, value=0)
        c = st.number_input("Column", min_value=0, max_value=st.session_state.builder["cols"] - 1, step=1, value=0)

        btn_cols = st.columns(2)
        with btn_cols[0]:
            if st.button("Place", type="primary", use_container_width=True, disabled=selected_block is None):
                ok = place_block(int(r), int(c), selected_block if selected_block else None)
                if not ok:
                    st.warning("No remaining blocks of that type. Earn more in Practice.")
        with btn_cols[1]:
            if st.button("Remove", use_container_width=True):
                place_block(int(r), int(c), None)

        st.caption("Tip: The Builder only lets you place blocks you still have remaining (earned minus already placed).")

    with colR:
        st.subheader("World Preview")
        # Show as emoji grid (simple & fast). Each rerun reflects changes.
        grid = grid_as_emojis()
        # Render as rows of emojis
        for row in grid:
            st.markdown("".join(row))

        # Optional: small legend for selected block
        if selected_block:
            img, emoji = get_block_visual(selected_block)
            st.caption(f"Selected: {emoji} {selected_block}")

