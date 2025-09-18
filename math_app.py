import random
import streamlit as st

st.set_page_config(page_title="Gui Gui Kids Math Trainer", page_icon="🧮", layout="centered")

 ---------- "Minecraft" blocks (emoji approximations) ----------
BLOCKS = [
    {"name": "Grass", "emoji": "🟩"},
    {"name": "Dirt", "emoji": "🟫"},
    {"name": "Stone", "emoji": "🪨"},
    {"name": "Wood", "emoji": "🪵"},
    {"name": "Brick", "emoji": "🧱"},
    {"name": "Sand", "emoji": "🟨"},
    {"name": "Water", "emoji": "🌊"},
    {"name": "Coal", "emoji": "⚫"},
    {"name": "Iron", "emoji": "⚙️"},
    {"name": "Gold", "emoji": "🟨⭐"},
    {"name": "Lapis", "emoji": "🔷"},
    {"name": "Redstone", "emoji": "🔴"},
    {"name": "Diamond", "emoji": "💎"},
    {"name": "Obsidian", "emoji": "⬛"},
    {"name": "TNT", "emoji": "🧨"},
]

# ---------- Helpers ----------
def gen_add(min_n, max_n):
    a = random.randint(min_n, max_n); b = random.randint(min_n, max_n)
    return a, b, "+", a + b

def gen_sub(min_n, max_n):
    a = random.randint(min_n, max_n); b = random.randint(min_n, max_n)
    if b > a: a, b = b, a
    return a, b, "−", a - b

def gen_mul(min_n, max_n):
    a = random.randint(min_n, max_n); b = random.randint(min_n, max_n)
    return a, b, "×", a * b

def gen_div(min_n, max_n):
    b = random.randint(max(min_n, 1), max_n)
    result = random.randint(min_n, max_n)
    a = b * result
    return a, b, "÷", result

def generate_questions(n, ops, min_n, max_n):
    qs = []
    for _ in range(n):
        op = random.choice(ops)
        if op == "+": a,b,sym,ans = gen_add(min_n,max_n)
        elif op == "−": a,b,sym,ans = gen_sub(min_n,max_n)
        elif op == "×": a,b,sym,ans = gen_mul(min_n,max_n)
        else: a,b,sym,ans = gen_div(min_n,max_n)
        qs.append({"a": a, "b": b, "op": sym, "answer": ans, "text": f"{a} {sym} {b} = ?"})
    return qs

def award_block():
    """Pick a random block and add to inventory; return it."""
    block = random.choice(BLOCKS)
    st.session_state.inventory.append(block["name"])
    return block

def reset_game(num_q=10, min_n=0, max_n=12, ops=None):
    if ops is None: ops = ["+", "−", "×", "÷"]
    st.session_state.questions = generate_questions(num_q, ops, min_n, max_n)
    st.session_state.idx = 0
    st.session_state.attempts_left = 3
    st.session_state.score = 0
    st.session_state.finished = False
    st.session_state.feedback = ""
    st.session_state.question_done = False
    st.session_state.last_correct = None
    st.session_state.user_answer = None
    st.session_state.inventory = []  # clear collected blocks for a fresh run

def inventory_counts():
    return Counter(st.session_state.inventory)

def inventory_display(compact=False):
    counts = inventory_counts()
    if not counts:
        st.caption("No blocks yet — answer correctly to collect some! ⛏️")
        return
    if compact:
        st.write("".join(
            (next(b["emoji"] for b in BLOCKS if b["name"] == name) + " ") * cnt
            for name, cnt in counts.items()
        ))
        return
    # Grid style
    st.write("**Your Blocks**")
    rows = []
    for name, cnt in sorted(counts.items()):
        emoji = next(b["emoji"] for b in BLOCKS if b["name"] == name)
        rows.append(f"- {emoji} **{name}** × **{cnt}**")
    st.markdown("\n".join(rows))

# ---------- Sidebar (settings for a new game) ----------
with st.sidebar:
    st.header("⚙️ Settings")
    num_q = st.slider("Number of questions", 5, 20, 10, 1)
    max_n = st.slider("Largest number", 5, 20, 12, 1)
    include_add = st.checkbox("Addition (+)", True)
    include_sub = st.checkbox("Subtraction (−)", True)
    include_mul = st.checkbox("Multiplication (×)", True)
    include_div = st.checkbox("Division (÷)", True)
    chosen_ops = []
    if include_add: chosen_ops.append("+")
    if include_sub: chosen_ops.append("−")
    if include_mul: chosen_ops.append("×")
    if include_div: chosen_ops.append("÷")
    if not chosen_ops:
        st.warning("Select at least one operation to include.")
    if st.button("🔄 Start new game", type="primary", use_container_width=True, disabled=not chosen_ops):
        reset_game(num_q=num_q, min_n=0, max_n=max_n, ops=chosen_ops)

    st.divider()
    st.subheader("🎒 Inventory")
    inventory_display(compact=False)

# ---------- Initialize state ----------
if "questions" not in st.session_state:
    reset_game()

# ---------- Header ----------
st.title("🧮 Kids Math Trainer")
st.caption("You have **3 attempts** for each question. Collect a **Minecraft-style block** with every correct answer! There are **10 exercises by default** (change in the sidebar).")

# ---------- Finished Screen ----------
if st.session_state.finished:
    total = len(st.session_state.questions)
    st.success(f"All done! Score: **{st.session_state.score} / {total}** 🎉")
    percent = int(round(100 * st.session_state.score / total))
    st.progress(percent / 100)
    if percent == 100:
        st.balloons()

    # Summary: inventory and Q&A
    st.divider()
    st.subheader("🎒 Your Block Collection")
    inventory_display(compact=False)

    with st.expander("See all questions and answers"):
        rows = []
        for q in st.session_state.questions:
            rows.append(f"{q['text'].replace('= ?', '= ' + str(q['answer']))}")
        st.markdown("\n".join([f"- {r}" for r in rows]))

    st.button("Play again", on_click=reset_game, type="primary")
    st.stop()

# ---------- Current Question ----------
idx = st.session_state.idx
total = len(st.session_state.questions)
q = st.session_state.questions[idx]
st.write(f"**Question {idx + 1} of {total}**")
st.progress((idx) / total)

# Quick compact inventory view under progress
with st.expander("Quick view: your blocks so far", expanded=False):
    inventory_display(compact=True)

st.markdown(f"### {q['text']}")
st.caption(f"Attempts left: **{st.session_state.attempts_left}**")

# ---------- Answer Form ----------
with st.form("answer_form", clear_on_submit=False):
    ans = st.number_input(
        "Your answer",
        value=st.session_state.user_answer if st.session_state.user_answer is not None else 0,
        step=1, format="%d"
    )
    submitted = st.form_submit_button("Check")

if submitted and not st.session_state.question_done:
    st.session_state.user_answer = int(ans)
    if int(ans) == q["answer"]:
        st.session_state.score += 1
        # Award a block on correct answer
        block = award_block()
        st.toast(f"You earned a {block['emoji']} **{block['name']}** block!", icon="✅")
        st.session_state.feedback = f"✅ Correct! You got a {block['emoji']} **{block['name']}** block!"
        st.session_state.question_done = True
        st.session_state.last_correct = True
    else:
        st.session_state.attempts_left -= 1
        if st.session_state.attempts_left > 0:
            st.session_state.feedback = f"❌ Not quite. Try again! Attempts left: {st.session_state.attempts_left}"
            st.session_state.last_correct = False
        else:
            st.session_state.feedback = f"❌ Out of attempts. The correct answer was **{q['answer']}**."
            st.session_state.question_done = True
            st.session_state.last_correct = False

# ---------- Feedback & Navigation ----------
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
st.caption("Tip: Customize question count and number range in the sidebar, then press **Start new game**.")
