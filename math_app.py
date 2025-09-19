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

def render_voxel_builder(inventory: Counter, world=None, grid_size=24, cell=1.0, free_build: bool=False, prefer_local: bool=False):
    """
    3D voxel editor:
      • Uses local Three.js if available (assets/libs/*), or if prefer_local=True.
      • Otherwise falls back to multiple CDNs (jsDelivr → unpkg → cdnjs).
      • Base64-embeds block textures (no image paths/CORS).
    """
    import base64, io, json as _json
    import streamlit.components.v1 as components
    from pathlib import Path

    names = [b["name"] for b in BLOCKS]

    def img_data_uri(name):
        img = BLOCK_IMAGES.get(name)
        if img is None:
            return None
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"

    textures = {n: img_data_uri(n) for n in names}
    colors   = {b["name"]: b["color"] for b in BLOCKS}
    emojis   = {b["name"]: b["emoji"] for b in BLOCKS}
    inv_map  = {k: int(v) for k, v in inventory.items()}
    world    = world if world else {"voxels": []}

    # -------- Local library detection --------
    lib_dir = Path("assets/libs")
    three_path = lib_dir / "three.min.js"
    orbit_path = lib_dir / "OrbitControls.js"
    use_local = prefer_local and three_path.exists() and orbit_path.exists()
    local_scripts = ""
    if use_local:
        three_js = three_path.read_text(encoding="utf-8")
        orbit_js = orbit_path.read_text(encoding="utf-8")
        # Inline the JS so browsers don’t block file:// in iframes
        local_scripts = "<script>" + three_js + "</script>\n<script>" + orbit_js + "</script>"

    html_template = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<title>3D Builder</title>
<style>
  html, body { margin:0; padding:0; height:100%; overflow:hidden; background:#111; }
  #ui {
    position: fixed; top: 10px; right: 10px; z-index: 9999;
    background: rgba(0,0,0,0.6); color: #fff; padding: 8px 10px; border-radius: 8px;
    font-family: system-ui, sans-serif; font-size: 14px; width: 260px; pointer-events: auto;
  }
  #ui select, #ui button, #ui input[type=file] {
    margin: 4px 0; width: 100%; background:#222; color:#fff; border:1px solid #444; border-radius:6px; padding:6px;
  }
  #inv { margin-top:6px; max-height: 160px; overflow:auto; }
  #inv div { display:flex; justify-content:space-between; }
  #msg {
    position: fixed; bottom: 10px; left: 50%; transform: translateX(-50%);
    color:#fff; background:rgba(0,0,0,0.4); padding:6px 10px; border-radius:6px; font-family: system-ui, sans-serif;
  }
  canvas { display:block; position:absolute; top:0; left:0; z-index:1; }
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
<div id="msg">Loading 3D…</div>

__LOCAL_LIBS__

<script>
(function() {
  const USE_LOCAL = __USE_LOCAL__;

  async function loadScript(src) {
    return new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = src; s.async = true;
      s.onload = () => resolve();
      s.onerror = () => reject(new Error("Failed " + src));
      document.head.appendChild(s);
    });
  }

  async function ensureThree() {
    if (USE_LOCAL) return true; // already inlined
    const threeURLs = [
      "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js",
      "https://unpkg.com/three@0.160.0/build/three.min.js",
      "https://cdnjs.cloudflare.com/ajax/libs/three.js/r160/three.min.js"
    ];
    const ocURLs = [
      "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/js/controls/OrbitControls.js",
      "https://unpkg.com/three@0.160.0/examples/js/controls/OrbitControls.js",
      "https://cdnjs.cloudflare.com/ajax/libs/three.js/r160/examples/js/controls/OrbitControls.min.js",
      "https://cdnjs.cloudflare.com/ajax/libs/three.js/r160/examples/js/controls/OrbitControls.js"
    ];
    for (const u of threeURLs) { try { await loadScript(u); break; } catch(e) {} }
    for (const u of ocURLs)    { try { await loadScript(u); break; } catch(e) {} }
    return !!(window.THREE && THREE.OrbitControls);
  }

  (async () => {
    const ok = await ensureThree();
    if (!ok) {
      document.body.innerHTML =
        '<div style="color:#fff;font-family:system-ui;padding:16px">⚠️ Failed to load Three.js (all CDNs blocked and no local libs).<br/>Add files to <code>assets/libs/</code> or allow one CDN.</div>';
      return;
    }

    const GRID_SIZE = __GRID_SIZE__;
    const CELL = __CELL__;
    const FREE_BUILD = __FREE_BUILD__;
    const NAMES    = __NAMES__;
    const textures = __TEXTURES__;
    const colors   = __COLORS__;
    const emojis   = __EMOJIS__;
    let inventory  = __INV__;
    let world      = __WORLD__;

    if (Object.keys(inventory).length === 0) {
      inventory = Object.fromEntries(NAMES.map(n => [n, FREE_BUILD ? 9999 : 0]));
    }

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x111111);
    const camera = new THREE.PerspectiveCamera(60, window.innerWidth/window.innerHeight, 0.1, 2000);
    camera.position.set(15, 18, 22);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.shadowMap.enabled = true;
    document.body.appendChild(renderer.domElement);

    const ui = document.getElementById("ui");
    ui.addEventListener("pointerdown", e => e.stopPropagation());
    ui.addEventListener("click", e => e.stopPropagation());

    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true; controls.dampingFactor = 0.05; controls.target.set(0, 0, 0);

    const ambient = new THREE.AmbientLight(0xffffff, 0.6); scene.add(ambient);
    const dir = new THREE.DirectionalLight(0xffffff, 0.8); dir.position.set(20,30,10); dir.castShadow = true; scene.add(dir);

    const gridHelper = new THREE.GridHelper(GRID_SIZE*2, GRID_SIZE*2, 0x444444, 0x222222);
    gridHelper.rotation.x = Math.PI/2; scene.add(gridHelper);

    const planeGeo = new THREE.PlaneGeometry(GRID_SIZE*2, GRID_SIZE*2); planeGeo.rotateX(-Math.PI/2);
    const plane = new THREE.Mesh(planeGeo, new THREE.MeshBasicMaterial({ visible:false })); scene.add(plane);

    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const texCache = new Map();
    function makeMaterial(name) {
      const url = textures[name];
      if (url) {
        if (!texCache.has(url)) {
          const loader = new THREE.TextureLoader();
          const t = loader.load(url);
          t.magFilter = THREE.NearestFilter; t.minFilter = THREE.LinearMipMapLinearFilter;
          texCache.set(url, t);
        }
        return new THREE.MeshStandardMaterial({ map: texCache.get(url) });
      }
      return new THREE.MeshStandardMaterial({ color: new THREE.Color(colors[name]||"#cccccc") });
    }

    const cubeGeo = new THREE.BoxGeometry(CELL, CELL, CELL);
    const voxelGroup = new THREE.Group(); scene.add(voxelGroup);
    function key(x,y,z) { return x + '|' + y + '|' + z; }
    const voxels = new Map(); const voxelData = new Map();

    function placeVoxel(x,y,z,name) {
      const k = key(x,y,z); if (voxels.has(k)) return false;
      if (!FREE_BUILD) {
        if (!inventory[name] || inventory[name] <= 0) return false;
      }
      const mesh = new THREE.Mesh(cubeGeo, makeMaterial(name));
      mesh.castShadow = true; mesh.receiveShadow = true;
      mesh.position.set(x+CELL/2, y+CELL/2, z+CELL/2);
      voxelGroup.add(mesh); voxels.set(k, mesh); voxelData.set(k, { name });
      if (!FREE_BUILD) { inventory[name] -= 1; refreshUI(); }
      return true;
    }
    function removeVoxel(x,y,z) {
      const k = key(x,y,z); if (!voxels.has(k)) return false;
      const mesh = voxels.get(k); const info = voxelData.get(k);
      voxelGroup.remove(mesh); mesh.geometry.dispose();
      if (mesh.material.map) mesh.material.map.dispose(); mesh.material.dispose();
      voxels.delete(k); voxelData.delete(k);
      if (!FREE_BUILD && info && info.name) { inventory[info.name] = (inventory[info.name]||0) + 1; refreshUI(); }
      return true;
    }

    const blockSel = document.getElementById("blockSel");
    function refreshDropdown() {
      const prev = blockSel.value;
      blockSel.innerHTML = "";
      let first = null;
      const keys = FREE_BUILD ? NAMES : Array.from(new Set([...NAMES, ...Object.keys(inventory)]));
      keys.forEach(name => {
        const cnt = inventory[name] ?? (FREE_BUILD ? 9999 : 0);
        const opt = document.createElement("option");
        opt.value = name;
        opt.textContent = (emojis[name]||"") + " " + name + " (" + (FREE_BUILD ? "∞" : cnt) + ")";
        if (!FREE_BUILD && cnt === 0) opt.disabled = true;
        blockSel.appendChild(opt);
        if (first === null && (!opt.disabled)) first = name;
      });
      const enabled = Array.from(blockSel.options).filter(o => !o.disabled);
      if (enabled.length) {
        blockSel.value = (prev && !blockSel.querySelector(`option[value="${prev}"]`)?.disabled) ? prev : first;
      } else {
        const opt = document.createElement("option");
        opt.textContent = "No blocks available — earn some in Practice";
        opt.disabled = true; opt.selected = true;
        blockSel.appendChild(opt);
      }
    }

    function refreshInventory() {
      const invDiv = document.getElementById("inv");
      invDiv.innerHTML = "<b>Inventory</b>";
      const keys = FREE_BUILD ? NAMES : Object.keys(inventory);
      keys.forEach(name => {
        const cnt = inventory[name] ?? (FREE_BUILD ? "∞" : 0);
        const row = document.createElement("div");
        row.innerHTML = "<span>" + (emojis[name]||"") + " " + name + "</span><span>× " + cnt + "</span>";
        invDiv.appendChild(row);
      });
    }

    function refreshUI() {
      refreshDropdown();
      refreshInventory();
      document.getElementById("msg").textContent =
        "Left click: place • Shift/Right click: remove • Drag: orbit • Scroll: zoom";
    }

    refreshUI();

    function loadWorld(w) {
      for (const [k,m] of voxels) {
        voxelGroup.remove(m); m.geometry.dispose(); if (m.material.map) m.material.map.dispose(); m.material.dispose();
      }
      voxels.clear(); voxelData.clear();
      if (!w || !w.voxels) return;
      w.voxels.forEach(v => {
        const mesh = new THREE.Mesh(cubeGeo, makeMaterial(v.name));
        mesh.castShadow = true; mesh.receiveShadow = true;
        mesh.position.set(v.x+CELL/2, v.y+CELL/2, v.z+CELL/2);
        voxelGroup.add(mesh);
        const k = key(v.x,v.y,v.z); voxels.set(k, mesh); voxelData.set(k, { name: v.name });
      });
    }
    loadWorld(world);

    function onPointerDown(event) {
      event.preventDefault();
      const rect = renderer.domElement.getBoundingClientRect();
      const mouse = new THREE.Vector2(
        ((event.clientX - rect.left) / rect.width) * 2 - 1,
        -((event.clientY - rect.top) / rect.height) * 2 + 1
      );
      const raycaster = new THREE.Raycaster();
      raycaster.setFromCamera(mouse, camera);

      const pickVox   = raycaster.intersectObjects(Array.from(voxels.values()), false)[0];
      const pickPlane = raycaster.intersectObject(plane, false)[0];
      const wantRemove = (event.shiftKey) || (event.button === 2);

      if (wantRemove && pickVox) {
        const p = pickVox.object.position.clone().subScalar(CELL/2);
        const x = Math.round(p.x / CELL) * CELL;
        const y = Math.round(p.y / CELL) * CELL;
        const z = Math.round(p.z / CELL) * CELL;
        removeVoxel(x,y,z); return;
      }

      if (pickVox && !wantRemove) {
        const n = pickVox.face.normal.clone();
        const p = pickVox.object.position.clone().subScalar(CELL/2).addScaledVector(n, CELL);
        const x = Math.round(p.x / CELL) * CELL;
        const y = Math.round(p.y / CELL) * CELL;
        const z = Math.round(p.z / CELL) * CELL;
        placeVoxel(x,y,z, blockSel.value); return;
      }

      if (pickPlane && !wantRemove) {
        const p = pickPlane.point.clone();
        const x = Math.round(p.x / CELL) * CELL;
        const y = 0;
        const z = Math.round(p.z / CELL) * CELL;
        placeVoxel(x,y,z, blockSel.value);
      }
    }
    renderer.domElement.addEventListener("pointerdown", onPointerDown);
    renderer.domElement.addEventListener("contextmenu", e => e.preventDefault());

    window.addEventListener("resize", () => {
      camera.aspect = window.innerWidth/window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    });

    function animate() { requestAnimationFrame(animate); controls.update(); renderer.render(scene, camera); }
    animate();
  })();
})();
</script>
</body>
</html>
"""
    html = (html_template
            .replace("__LOCAL_LIBS__", local_scripts)
            .replace("__USE_LOCAL__", "true" if use_local else "false")
            .replace("__GRID_SIZE__", str(grid_size))
            .replace("__CELL__", str(cell))
            .replace("__FREE_BUILD__", str(free_build).lower())
            .replace("__NAMES__", _json.dumps(names))
            .replace("__TEXTURES__", _json.dumps(textures))
            .replace("__COLORS__", _json.dumps(colors))
            .replace("__EMOJIS__", _json.dumps(emojis))
            .replace("__INV__", _json.dumps(inv_map))
            .replace("__WORLD__", _json.dumps(world))
           )
    components.html(html, height=720, scrolling=False)
