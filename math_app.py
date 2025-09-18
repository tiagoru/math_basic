import random
from collections import Counter
from pathlib import Path

import streamlit as st
from PIL import Image

# -------------------- App setup --------------------
st.set_page_config(page_title="Gui Gui Math Trainer + 3D Builder", page_icon="🧮", layout="wide")

# -------------------- Assets & Blocks --------------------
ASSET_DIR = Path("assets/blocks")

BLOCKS = [
    {"name": "Grass",        "emoji": "🟩", "file": "grass.png",         "weight": 8, "color": "#57a639"},
    {"name": "Dirt",         "emoji": "🟫", "file": "dirt.png",          "weight": 8, "color": "#7a5230"},
    {"name": "Stone",        "emoji": "🪨", "file": "stone.png",         "weight": 8, "color": "#8e8e8e"},
    {"name": "Oak Planks",   "emoji": "🪵", "file": "oak_planks.png",    "weight": 6, "color": "#c89a5b"},
    {"name": "Brick",        "emoji": "🧱", "file": "brick.png",         "weight": 5, "color": "#b33a3a"},
    {"name": "Sand",         "emoji": "🟨", "file": "sand.png",          "weight": 6, "color": "#e7d9a8"},
    {"name": "Water",        "emoji": "🌊", "file": "water.png",         "weight": 5, "color": "#3aa0ff"},
    {"name": "Coal Ore",     "emoji": "⚫", "file": "coal_ore.png",      "weight": 4, "color": "#2b2b2b"},
    {"name": "Iron Ore",     "emoji": "⚙️", "file": "iron_ore.png",      "weight": 3, "color": "#b0b0b0"},
    {"name": "Gold Ore",     "emoji": "⭐", "file": "gold_ore.png",      "weight": 2, "color": "#ffd24a"},
    {"name": "Lapis Ore",    "emoji": "🔷", "file": "lapis_ore.png",     "weight": 2, "color": "#2a62ff"},
    {"name": "Redstone Ore", "emoji": "🔴", "file": "redstone_ore.png",  "weight": 2, "color": "#ff3a3a"},
    {"name": "Diamond Ore",  "emoji": "💎", "file": "diamond_ore.png",   "weight": 1, "color": "#2ef5d0"},
    {"name": "Obsidian",     "emoji": "⬛", "file": "obsidian.png",      "weight": 1, "color": "#1a1226"},
    {"name": "TNT",          "emoji": "🧨", "file": "tnt.png",           "weight": 1, "color": "#ff4a4a"},
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

def has_texture(name: str) -> bool:
    return BLOCK_IMAGES.get(name) is not None

def texture_path(name: str) -> str:
    f = next(b["file"] for b in BLOCKS if b["name"] == name)
    return str((ASSET_DIR / f).as_posix())

def block_color(name: str) -> str:
    return next(b["color"] for b in BLOCKS if b["name"] == name)

def get_block_emoji(name: str) -> str:
    return next(b["emoji"] for b in BLOCKS if b["name"] == name)

# -------------------- Math generators --------------------
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

# -------------------- Game state helpers --------------------
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
    if "inventory" not in st.session_state:
        st.session_state.inventory = []  # list of block names earned

def award_block():
    names = [b["name"] for b in BLOCKS]
    weights = [b["weight"] for b in BLOCKS]
    choice = random.choices(names, weights=weights, k=1)[0]
    st.session_state.inventory.append(choice)
    return choice

def inventory_counts() -> Counter:
    return Counter(st.session_state.get("inventory", []))

# -------------------- 3D builder component --------------------
def render_voxel_builder(inventory: Counter, world=None, grid_size=20, cell=1.0):
    """Embedded Three.js voxel editor with robust dropdown even at 0 inventory."""
    import json as _json
    import streamlit.components.v1 as components

    names = [b["name"] for b in BLOCKS]
    textures = {n: (texture_path(n) if has_texture(n) else None) for n in names}
    colors = {b["name"]: b["color"] for b in BLOCKS}
    emojis = {b["name"]: b["emoji"] for b in BLOCKS}
    inv_map = {k: int(v) for k, v in inventory.items()}

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<title>3D Builder</title>
<style>
  html, body {{ margin:0; padding:0; height:100%; overflow:hidden; background:#111; }}
  #ui {{
    position: absolute; top: 10px; right: 10px; z-index: 9999;
    background: rgba(0,0,0,0.6); color: #fff; padding: 8px 10px; border-radius: 8px;
    font-family: system-ui, sans-serif; font-size: 14px; width: 240px;
  }}
  #ui select, #ui button, #ui input[type=file] {{
    margin: 4px 0; width: 100%; background:#222; color:#fff; border:1px solid #444; border-radius:6px; padding:6px;
  }}
  #inv {{ margin-top:6px; max-height: 160px; overflow:auto; }}
  #inv div {{ display:flex; justify-content:space-between; }}
  #msg {{
    position: absolute; bottom: 10px; left: 50%; transform: translateX(-50%);
    color:#fff; background:rgba(0,0,0,0.4); padding:6px 10px; border-radius:6px; font-family: system-ui, sans-serif;
  }}
  canvas {{ display:block; position:absolute; top:0; left:0; z-index:1; }}
</style>
</head>
<body>
<div id="ui">
  <div><b>Block</b></div>
  <select id="blockSel"></select>
  <button id="modeBtn" title="Toggle place/remove">Mode: Place</button>
  <button id="saveBtn">💾 Save JSON</button>
  <input id="loadFile" type="file" accept="application/json"/>
  <div id="inv"><b>Inventory</b></div>
</div>
<div id="msg">Left click: place • Shift/Right click: remove • Drag: orbit • Scroll: zoom</div>

<script type="module">
import * as THREE from "https://unpkg.com/three@0.160.0/build/three.module.js";
import {{ OrbitControls }} from "https://unpkg.com/three@0.160.0/examples/jsm/controls/OrbitControls.js";

const GRID_SIZE = {grid_size};
const CELL = {cell};
const NAMES = {_json.dumps(names)};
const textures = {_json.dumps(textures)};
const colors = {_json.dumps(colors)};
const emojis = {_json.dumps(emojis)};
let inventory = {_json.dumps(inv_map)};
let world = {_json.dumps(world if world else {"voxels": []})};

// If you have no blocks yet, still show dropdown (disabled options)
if (Object.keys(inventory).length === 0) {{
  inventory = Object.fromEntries(NAMES.map(n => [n, 0]));
}}

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x111111);
const camera = new THREE.PerspectiveCamera(60, window.innerWidth/window.innerHeight, 0.1, 2000);
camera.position.set(15, 18, 22);

const renderer = new THREE.WebGLRenderer({{ antialias: true }});
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
document.body.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true; controls.dampingFactor = 0.05; controls.target.set(0, 0, 0);

const ambient = new THREE.AmbientLight(0xffffff, 0.6); scene.add(ambient);
const dir = new THREE.DirectionalLight(0xffffff, 0.8); dir.position.set(20,30,10); dir.castShadow = true; scene.add(dir);

const gridHelper = new THREE.GridHelper(GRID_SIZE*2, GRID_SIZE*2, 0x444444, 0x222222);
gridHelper.rotation.x = Math.PI/2; scene.add(gridHelper);

const planeGeo = new THREE.PlaneGeometry(GRID_SIZE*2, GRID_SIZE*2); planeGeo.rotateX(-Math.PI/2);
const plane = new THREE.Mesh(planeGeo, new THREE.MeshBasicMaterial({{ visible:false }})); scene.add(plane);

const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();

const texCache = new Map();
function makeMaterial(name) {{
  const url = textures[name];
  if (url) {{
    if (!texCache.has(url)) {{
      const t = new THREE.TextureLoader().load(url);
      t.magFilter = THREE.NearestFilter; t.minFilter = THREE.LinearMipMapLinearFilter;
      texCache.set(url, t);
    }}
    return new THREE.MeshStandardMaterial({{ map: texCache.get(url) }});
  }}
  return new THREE.MeshStandardMaterial({{ color: new THREE.Color(colors[name]||"#cccccc") }});
}}

const cubeGeo = new THREE.BoxGeometry(CELL, CELL, CELL);
const voxelGroup = new THREE.Group(); scene.add(voxelGroup);
function key(x,y,z) {{ return `${{x}}|${{y}}|${{z}}`; }}
const voxels = new Map(); const voxelData = new Map();

function placeVoxel(x,y,z,name) {{
  const k = key(x,y,z); if (voxels.has(k)) return false;
  if (!inventory[name] || inventory[name] <= 0) return false;
  const mesh = new THREE.Mesh(cubeGeo, makeMaterial(name));
  mesh.castShadow = true; mesh.receiveShadow = true;
  mesh.position.set(x+CELL/2, y+CELL/2, z+CELL/2);
  voxelGroup.add(mesh); voxels.set(k, mesh); voxelData.set(k, {{ name }});
  inventory[name] -= 1; refreshInventory(); refreshDropdown();
  return true;
}}
function removeVoxel(x,y,z) {{
  const k = key(x,y,z); if (!voxels.has(k)) return false;
  const mesh = voxels.get(k); const info = voxelData.get(k);
  voxelGroup.remove(mesh); mesh.geometry.dispose();
  if (mesh.material.map) mesh.material.map.dispose(); mesh.material.dispose();
  voxels.delete(k); voxelData.delete(k);
  if (info && info.name) {{ inventory[info.name] = (inventory[info.name]||0) + 1; }}
  refreshInventory(); refreshDropdown(); return true;
}}

const blockSel = document.getElementById("blockSel");
function refreshDropdown() {{
  const prev = blockSel.value;
  blockSel.innerHTML = "";
  let firstEnabled = null;
  Object.keys(inventory).forEach(name => {{
    const cnt = inventory[name]||0;
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = `${{emojis[name]||""}} ${{name}} (${{cnt}})`;
    if (cnt === 0) opt.disabled = true;
    blockSel.appendChild(opt);
    if (cnt > 0 && firstEnabled === null) firstEnabled = name;
  }});
  if (blockSel.querySelectorAll("option:not([disabled])").length === 0) {{
    const opt = document.createElement("option");
    opt.textContent = "No blocks available — earn some in Practice";
    opt.disabled = true; opt.selected = true;
    blockSel.appendChild(opt);
  }} else {{
    blockSel.value = (prev && inventory[prev] > 0) ? prev : firstEnabled;
  }}
}}

function refreshInventory() {{
  const invDiv = document.getElementById("inv");
  invDiv.innerHTML = "<b>Inventory</b>";
  Object.keys(inventory).forEach(name => {{
    const row = document.createElement("div");
    row.innerHTML = `<span>${{emojis[name]||""}} ${{name}}</span><span>× ${{inventory[name]||0}} </span>`;
    invDiv.appendChild(row);
  }});
  const any = Object.values(inventory).some(v => v > 0);
  document.getElementById("msg").textContent = any
    ? "Left click: place • Shift/Right click: remove • Drag: orbit • Scroll: zoom"
    : "No blocks available — earn some in Practice. You can still look around.";
}}
refreshInventory(); refreshDropdown();

// Load existing world without charging inventory (treat as already paid)
function loadWorld(w) {{
  for (const [k,m] of voxels) {{
    voxelGroup.remove(m); m.geometry.dispose(); if (m.material.map) m.material.map.dispose(); m.material.dispose();
  }}
  voxels.clear(); voxelData.clear();
  if (!w || !w.voxels) return;
  w.voxels.forEach(v => {{
    const mesh = new THREE.Mesh(cubeGeo, makeMaterial(v.name));
    mesh.castShadow = true; mesh.receiveShadow = true;
    mesh.position.set(v.x+CELL/2, v.y+CELL/2, v.z+CELL/2);
    voxelGroup.add(mesh);
    const k = key(v.x,v.y,v.z); voxels.set(k, mesh); voxelData.set(k, {{ name: v.name }});
  }});
}}

loadWorld(world);

// UI buttons
let mode = "place";
const modeBtn = document.getElementById("modeBtn");
modeBtn.onclick = () => {{
  mode = (mode === "place") ? "remove" : "place";
  modeBtn.textContent = "Mode: " + (mode === "place" ? "Place" : "Remove");
}};

document.getElementById("saveBtn").onclick = () => {{
  const data = {{ voxels: [] }};
  for (const [k,info] of voxelData) {{
    const [x,y,z] = k.split("|").map(Number);
    data.voxels.push({{ x, y, z, name: info.name }});
  }}
  const blob = new Blob([JSON.stringify(data,null,2)], {{type:"application/json"}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a"); a.href = url; a.download = "world3d.json"; a.click();
  URL.revokeObjectURL(url);
}};

document.getElementById("loadFile").addEventListener("change", (e) => {{
  const f = e.target.files[0]; if (!f) return;
  const r = new FileReader();
  r.onload = () => {{ try {{ loadWorld(JSON.parse(r.result)); }} catch(e) {{ alert("Bad JSON: "+e); }} }};
  r.readAsText(f);
}});

// Mouse interaction
function onPointerDown(event) {{
  event.preventDefault();
  const rect = renderer.domElement.getBoundingClientRect();
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(mouse, camera);

  const pickVox = raycaster.intersectObjects(Array.from(voxels.values()), false)[0];
  const pickPlane = raycaster.intersectObject(plane, false)[0];
  const wantRemove = (mode === "remove") || event.button === 2 || event.shiftKey;

  if (wantRemove && pickVox) {{
    const p = pickVox.object.position.clone().subScalar(CELL/2);
    const x = Math.round(p.x / CELL) * CELL;
    const y = Math.round(p.y / CELL) * CELL;
    const z = Math.round(p.z / CELL) * CELL;
    removeVoxel(x,y,z); return;
  }}

  if (pickVox && !wantRemove) {{
    const n = pickVox.face.normal.clone();
    const p = pickVox.object.position.clone().subScalar(CELL/2).addScaledVector(n, CELL);
    const x = Math.round(p.x / CELL) * CELL;
    const y = Math.round(p.y / CELL) * CELL;
    const z = Math.round(p.z / CELL) * CELL;
    const sel = blockSel.value;
    if (sel && (inventory[sel]||0) > 0) placeVoxel(x,y,z, sel);
    return;
  }}

  if (pickPlane && !wantRemove) {{
    const p = pickPlane.point.clone();
    const x = Math.round(p.x / CELL) * CELL;
    const y = 0;
    const z = Math.round(p.z / CELL) * CELL;
    const sel = blockSel.value;
    if (sel && (inventory[sel]||0) > 0) placeVoxel(x,y,z, sel);
  }}
}}
renderer.domElement.addEventListener("pointerdown", onPointerDown);
renderer.domElement.addEventListener("contextmenu", e => e.preventDefault());

window.addEventListener("resize", () => {{
  camera.aspect = window.innerWidth/window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
}});

function animate() {{ requestAnimationFrame(animate); controls.update(); renderer.render(scene, camera); }}
animate();
</script>
</body>
</html>
"""
    components.html(html, height=720, scrolling=False)

# -------------------- Initialize state BEFORE UI --------------------
if "questions" not in st.session_state:
    reset_game()

# -------------------- Tabs --------------------
tab_practice, tab_builder3d = st.tabs(["🧮 Practice", "🧱 3D Builder"])

# ==================== PRACTICE TAB ====================
with tab_practice:
    with st.sidebar:
        st.header("⚙️ Practice Settings")
        n_questions = st.slider("Number of questions", 5, 20, 10, 1, key="pq_num_q")
        max_n = st.slider("Largest number", 5, 1000, 12, 1, key="pq_max_n")
        include_add = st.checkbox("Addition (+)", True, key="pq_add")
        include_sub = st.checkbox("Subtraction (−)", True, key="pq_sub")
        include_mul = st.checkbox("Multiplication (×)", True, key="pq_mul")
        include_div = st.checkbox("Division (÷)", True, key="pq_div")

        ops = []
        if include_add: ops.append("+")
        if include_sub: ops.append("−")
        if include_mul: ops.append("×")
        if include_div: ops.append("÷")

        if not ops:
            st.warning("Select at least one operation to include.")

        if st.button("🔄 Start new game", type="primary", use_container_width=True, disabled=not ops):
            reset_game(num_q=n_questions, min_n=0, max_n=max_n, ops=ops)
            st.rerun()

        st.divider()
        st.subheader("🎒 Inventory (earned blocks)")
        inv_counts = inventory_counts()
        if inv_counts:
            for name, cnt in sorted(inv_counts.items()):
                st.write(f"{get_block_emoji(name)} **{name}** × **{cnt}**")
        else:
            st.caption("No blocks yet — answer correctly to collect some! ⛏️")

    st.title("🧮 Kids Math Trainer")
    st.caption("3 attempts per question. Correct answers award blocks. Number range up to 1000 (see sidebar).")

    # Finished screen
    if st.session_state.finished:
        n_total = len(st.session_state.questions)
        st.success(f"All done! Score: **{st.session_state.score} / {n_total}** 🎉")
        pct = int(round(100 * st.session_state.score / max(n_total, 1)))
        st.progress(pct / 100)
        if pct == 100: st.balloons()
        with st.expander("See all questions and answers"):
            rows = [f"{q['text'].replace('= ?', '= ' + str(q['answer']))}" for q in st.session_state.questions]
            st.markdown("\n".join(f"- {r}" for r in rows))
        st.stop()

    # Current question
    idx = int(st.session_state.idx)
    n_total = len(st.session_state.questions)
    # Guard: if idx ever drifts out of range, finish gracefully
    if idx >= n_total:
        st.session_state.finished = True
        st.rerun()

    q = st.session_state.questions[idx]
    st.write(f"**Question {idx + 1} of {n_total}**")
    st.progress(idx / max(n_total, 1))

    st.markdown(f"### {q['text']}")
    st.caption(f"Attempts left: **{st.session_state.attempts_left}**")

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
            won = award_block()
            st.toast(f"You earned a {get_block_emoji(won)} {won} block!", icon="✅")
            st.session_state.feedback = f"✅ Correct! You got a **{won}** block!"
            st.session_state.question_done = True
        else:
            st.session_state.attempts_left -= 1
            if st.session_state.attempts_left > 0:
                st.session_state.feedback = f"❌ Not quite. Try again! Attempts left: {st.session_state.attempts_left}"
            else:
                st.session_state.feedback = f"❌ Out of attempts. The correct answer was **{q['answer']}**."
                st.session_state.question_done = True

    if st.session_state.feedback:
        (st.info if st.session_state.question_done else st.warning)(st.session_state.feedback)

    c1, c2 = st.columns(2)
    with c1:
        if st.session_state.question_done:
            if st.button("➡️ Next question", type="primary", use_container_width=True):
                st.session_state.idx += 1
                st.session_state.attempts_left = 3
                st.session_state.feedback = ""
                st.session_state.question_done = False
                st.session_state.user_answer = None
                if st.session_state.idx >= len(st.session_state.questions):
                    st.session_state.finished = True
                st.rerun()
    with c2:
        if st.button("🔁 Restart practice (keep blocks)", use_container_width=True):
            reset_game(num_q=st.session_state.get("pq_num_q", 10),
                       min_n=0,
                       max_n=st.session_state.get("pq_max_n", 12),
                       ops=[op for op, on in zip(["+","−","×","÷"],
                           [st.session_state.get("pq_add",True),
                            st.session_state.get("pq_sub",True),
                            st.session_state.get("pq_mul",True),
                            st.session_state.get("pq_div",True)]) if on])
            st.rerun()

# ==================== 3D BUILDER TAB ====================
with tab_builder3d:
    st.title("🧱 3D Builder (voxel world)")
    st.caption("Use your earned blocks to build in 3D. Left click to place, Shift/Right click to remove, drag to orbit, scroll to zoom. Save/load JSON inside the 3D panel.")

    # Optional: quick seed to test the dropdown/UI
    with st.expander("Dev: grant a few test blocks"):
        if st.button("➕ Grant 5 Stone & 3 Grass"):
            st.session_state.inventory += ["Stone"] * 5 + ["Grass"] * 3
            st.rerun()

    inv_counts = inventory_counts()
    if not inv_counts:
        st.warning("You don't have any blocks yet. Earn some in the Practice tab! 😊")

    render_voxel_builder(inv_counts, world=None, grid_size=24, cell=1.0)
