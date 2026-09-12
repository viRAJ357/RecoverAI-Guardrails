import os

OUT = r"C:\Users\nikhi\Downloads\AI-Revenue-recovery-421\assets"
os.makedirs(OUT, exist_ok=True)

COLORS = [
    "#ff0055","#ff4400","#ff8800","#ffcc00","#aaff00",
    "#00ff88","#00ffcc","#00ccff","#0088ff","#4400ff",
    "#aa00ff","#ff00ff","#ff0099","#ff5577"
]

DEFS_BASE = """  <defs>
    <filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="4" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="glow2" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="8" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>"""

# ─────────────────────────────────────────────────────────────
# HELPER: animated dashed line
def dline(x1,y1,x2,y2,col,dur="0.8s"):
    return f'''<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="3" stroke-dasharray="12,8" filter="url(#glow)">
      <animate attributeName="stroke-dashoffset" from="20" to="0" dur="{dur}" repeatCount="indefinite"/>
    </line>'''

def node(x,y,w,h,col,text_lines,rx=12,font=13):
    svg = f'''<rect x="{x-w//2}" y="{y-h//2}" width="{w}" height="{h}" rx="{rx}" fill="{col}" fill-opacity="0.15" stroke="{col}" stroke-width="2.5" filter="url(#glow)"/>'''
    if isinstance(text_lines, str):
        text_lines = [text_lines]
    step = font + 4
    start_y = y - (len(text_lines)-1)*step/2
    for i,line in enumerate(text_lines):
        svg += f'<text x="{x}" y="{start_y + i*step + 4}" font-family="Consolas,monospace" font-size="{font}" font-weight="bold" fill="{col}" text-anchor="middle" filter="url(#glow)">{line}</text>'
    return svg

def arrow_down(x, y1, y2, col):
    return (dline(x,y1,x,y2,col) +
            f'<polygon points="{x},{y2} {x-7},{y2-12} {x+7},{y2-12}" fill="{col}" filter="url(#glow)"/>')

def label(x,y,text,col,size=12):
    return f'<text x="{x}" y="{y}" font-family="Consolas,monospace" font-size="{size}" font-weight="bold" fill="{col}" text-anchor="middle" filter="url(#glow)">{text}</text>'

# ─────────────────────────────────────────────────────────────
# SVG A: GUARDRAILS BRANCHING — FULL COLOR
# ─────────────────────────────────────────────────────────────
def make_guardrails():
    w, h = 1000, 900
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%">\n'
    svg += DEFS_BASE
    svg += f'<rect width="{w}" height="{h}" fill="#090a0f" rx="16"/>\n'

    # Title
    svg += f'<text x="500" y="45" font-family="Consolas,monospace" font-size="22" font-weight="bold" fill="#ffffff" text-anchor="middle" filter="url(#glow2)">🛡️  GUARDRAILS / AI SAFETY WORKFLOW</text>\n'

    # PAYMENT FAILURE node
    svg += node(500, 110, 360, 60, "#ff0055", ["PAYMENT FAILURE", "EVENT ARRIVES"])
    svg += arrow_down(500, 140, 200, "#ff4400")

    # GUARDRAIL ENGINE box
    svg += f'<rect x="130" y="200" width="740" height="200" rx="14" fill="#ff8800" fill-opacity="0.08" stroke="#ff8800" stroke-width="2.5" filter="url(#glow)"/>'
    svg += label(500, 228, "⚙️  GUARDRAIL ENGINE — 5 RULES", "#ff8800", 16)

    rules = [
        ("🔴", "risk_score ≥ 80?", "#ff0055"),
        ("🔴", "error_reason = risk_check_failed?", "#ff2244"),
        ("🟠", "failed_attempts ≥ 4?", "#ff6600"),
        ("🟠", "amount > ₹50,000?", "#ffaa00"),
        ("🟡", "retry_count ≥ 3?", "#ddcc00"),
    ]
    for i,(emoji,rule,col) in enumerate(rules):
        ry = 252 + i*28
        svg += f'<circle cx="170" cy="{ry}" r="8" fill="{col}" filter="url(#glow)"/>'
        svg += f'<text x="190" y="{ry+5}" font-family="Consolas,monospace" font-size="13" font-weight="bold" fill="{col}" filter="url(#glow)">{rule}</text>'

    svg += arrow_down(500, 400, 475, "#aaff00")

    # DIAMOND decision
    svg += f'<polygon points="500,475 620,530 500,585 380,530" fill="#aaff00" fill-opacity="0.15" stroke="#aaff00" stroke-width="2.5" filter="url(#glow)"/>'
    svg += label(500, 535, "ANY RULE TRIGGERS?", "#aaff00", 14)

    # YES branch
    svg += dline(380, 530, 250, 650, "#ff0055")
    svg += f'<polygon points="250,650 243,638 257,638" fill="#ff0055" filter="url(#glow)"/>'
    svg += label(290, 610, "YES", "#ff0055", 14)
    svg += node(250, 710, 220, 80, "#ff0055", ["👁️  HUMAN REVIEW", "(Operator Approval)"])

    # NO branch
    svg += dline(620, 530, 750, 650, "#00ffcc")
    svg += f'<polygon points="750,650 743,638 757,638" fill="#00ffcc" filter="url(#glow)"/>'
    svg += label(710, 610, "NO", "#00ffcc", 14)
    svg += node(750, 710, 240, 80, "#00ccff", ["🧠 CATBOOST ML ENGINE", "policy.py · 26 features"])

    # Both merge to final decision
    svg += dline(750, 750, 750, 820, "#00ccff")
    svg += dline(750, 820, 500, 820, "#00ccff")
    svg += arrow_down(500, 820, 830, "#00ccff")

    # Recovery action
    actions = ["⚡ smart_retry", "⏰ smart_delay", "📩 send_notification", "🔇 silent_wait"]
    cols_a = ["#00ff88","#aaff00","#00ffcc","#0088ff"]
    svg += f'<rect x="180" y="830" width="640" height="55" rx="12" fill="#0055ff" fill-opacity="0.15" stroke="#0055ff" stroke-width="2" filter="url(#glow)"/>'
    svg += label(500, 853, "RECOVERY ACTION DECISION", "#0088ff", 14)
    for i,(act,col_a) in enumerate(zip(actions, cols_a)):
        ax = 230 + i*145
        svg += label(ax, 876, act, col_a, 11)

    svg += '</svg>'
    with open(os.path.join(OUT, "4_guardrails_safety.svg"), "w", encoding="utf-8") as f:
        f.write(svg)

# ─────────────────────────────────────────────────────────────
# SVG B: ML PIPELINE — FULL COLOR
# ─────────────────────────────────────────────────────────────
def make_ml_pipeline():
    stages = [
        ("RAW DATA", "#ff0055"), ("DATA CLEANING", "#ff4400"), ("MISSING VALUE HDL.", "#ff8800"),
        ("ENCODING", "#ffcc00"), ("FEATURE ENGINEERING", "#aaff00"), ("TRAIN / VAL SPLIT 80/20", "#00ff88"),
        ("MODEL TRAINING", "#00ffcc"), ("HYPERPARAM OPT.", "#00ccff"), ("EARLY STOPPING @163", "#0088ff"),
        ("MODEL EVALUATION", "#4400ff"), ("MODEL SELECTION", "#aa00ff"), ("MODEL SERIALIZATION", "#ff00ff"),
        ("INFERENCE ENGINE", "#ff0099"), ("PREDICTION OUTPUT", "#ff5577"),
    ]
    cols = 2
    rows = len(stages)//cols + (1 if len(stages)%cols else 0)
    w, h = 960, 120 + rows*110
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%">\n'
    svg += DEFS_BASE
    svg += f'<rect width="{w}" height="{h}" fill="#090a0f" rx="16"/>\n'
    svg += f'<text x="{w//2}" y="45" font-family="Consolas,monospace" font-size="22" font-weight="bold" fill="#ffffff" text-anchor="middle" filter="url(#glow2)">🧠  ADVANCED ML PIPELINE</text>\n'

    nodes_pos = []
    for i, (name, col) in enumerate(stages):
        row = i // cols
        col_idx = i % cols
        if row % 2 == 1:
            col_idx = cols - 1 - col_idx
        x = 250 + col_idx * 460
        y = 110 + row * 110
        nodes_pos.append((x, y, name, col))

    # Draw connecting path
    for i in range(len(nodes_pos)-1):
        x1,y1,_,c1 = nodes_pos[i]
        x2,y2,_,c2 = nodes_pos[i+1]
        svg += dline(x1, y1+30, x2 if x1==x2 else x1, y2-30 if x1==x2 else y1, c1)
        if x1 != x2:
            svg += dline(x1, y1, x2, y1, c1)
            svg += arrow_down(x2, y1, y2-30, c2)

    for x, y, name, col in nodes_pos:
        svg += node(x, y, 340, 60, col, name)

    svg += '</svg>'
    with open(os.path.join(OUT, "2_ml_pipeline.svg"), "w", encoding="utf-8") as f:
        f.write(svg)

# ─────────────────────────────────────────────────────────────
# SVG C: SYSTEM ARCHITECTURE LAYERS — FULL COLOR
# ─────────────────────────────────────────────────────────────
def make_arch():
    layers = [
        ("LAYER 1", "USER / OPERATOR", "#ff0055"),
        ("LAYER 2", "FRONTEND / OPERATOR DASHBOARD · HTML CSS JS", "#ff6600"),
        ("LAYER 3", "API GATEWAY / FASTAPI · UVICORN · CORS · SWAGGER", "#ffcc00"),
        ("LAYER 4", "BUSINESS LOGIC · REQUEST ROUTER · PAYLOAD HANDLER", "#aaff00"),
        ("LAYER 5", "🛡️  GUARDRAILS ENGINE · guardrails.py · 5 RULES", "#00ff88"),
        ("LAYER 6", "🧠  AI / ML INFERENCE ENGINE · CatBoost · policy.py · 26 FEATURES", "#00ccff"),
        ("LAYER 7", "🗃️  DATABASE / AUDIT TRAIL · SQLite · SQLAlchemy", "#4400ff"),
        ("LAYER 8", "📡  MONITORING / LOGGING · Audit Events · Operator Approval", "#ff00ff"),
    ]
    w, h = 1000, 130 + len(layers)*90
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%">\n'
    svg += DEFS_BASE
    svg += f'<rect width="{w}" height="{h}" fill="#090a0f" rx="16"/>\n'
    svg += f'<text x="500" y="45" font-family="Consolas,monospace" font-size="22" font-weight="bold" fill="#ffffff" text-anchor="middle" filter="url(#glow2)">🏗️  SYSTEM ARCHITECTURE — 8 LAYERS</text>\n'

    for i, (layer_label, name, col) in enumerate(layers):
        y = 80 + i * 90
        svg += f'<rect x="60" y="{y}" width="880" height="65" rx="10" fill="{col}" fill-opacity="0.12" stroke="{col}" stroke-width="2.5" filter="url(#glow)"/>'
        svg += f'<text x="110" y="{y+28}" font-family="Consolas,monospace" font-size="11" font-weight="bold" fill="{col}" fill-opacity="0.7" filter="url(#glow)">{layer_label}</text>'
        svg += f'<text x="500" y="{y+40}" font-family="Consolas,monospace" font-size="14" font-weight="bold" fill="{col}" text-anchor="middle" filter="url(#glow)">{name}</text>'

        if i < len(layers)-1:
            nc = layers[i+1][2]
            for xp in [430, 500, 570]:
                svg += dline(xp, y+65, xp, y+90, col if xp==500 else nc, "0.7s")

    svg += '</svg>'
    with open(os.path.join(OUT, "3_system_architecture.svg"), "w", encoding="utf-8") as f:
        f.write(svg)

# ─────────────────────────────────────────────────────────────
# SVG D: SECURITY ARCHITECTURE — FULL COLOR
# ─────────────────────────────────────────────────────────────
def make_security():
    w, h = 900, 580
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%">\n'
    svg += DEFS_BASE
    svg += f'<rect width="{w}" height="{h}" fill="#090a0f" rx="16"/>\n'
    svg += f'<text x="450" y="45" font-family="Consolas,monospace" font-size="22" font-weight="bold" fill="#ffffff" text-anchor="middle" filter="url(#glow2)">🔐  SECURITY ARCHITECTURE</text>\n'

    # Security boundary outer box
    svg += f'<rect x="40" y="70" width="820" height="460" rx="16" fill="none" stroke="#00ffcc" stroke-width="3" stroke-dasharray="18,10" filter="url(#glow)"><animate attributeName="stroke-dashoffset" from="28" to="0" dur="1s" repeatCount="indefinite"/></rect>'
    svg += label(450, 100, "🔒  SECURITY BOUNDARY", "#00ffcc", 16)

    sections = [
        ("INPUT VALIDATION (Pydantic)", "#00ccff", [
            "• Type checking on all 26 fields",
            "• Range validation (risk_score 0-100)",
            "• Required field enforcement",
        ]),
        ("GUARDRAILS LAYER", "#ff8800", [
            "• Hard-coded financial rules — 5 rules",
            "• Cannot be overridden by ML model",
            "• Prevents model hallucination",
        ]),
        ("CORS MIDDLEWARE", "#aaff00", [
            "• Configurable origin control",
            "• FastAPI built-in CORS handler",
        ]),
    ]

    y_offset = 130
    for title, col, items in sections:
        svg += f'<rect x="70" y="{y_offset}" width="760" height="{40 + len(items)*26}" rx="10" fill="{col}" fill-opacity="0.08" stroke="{col}" stroke-width="2" filter="url(#glow)"/>'
        svg += label(450, y_offset+22, title, col, 15)
        for j, item in enumerate(items):
            svg += f'<text x="110" y="{y_offset+46+j*26}" font-family="Consolas,monospace" font-size="13" fill="{col}" filter="url(#glow)">{item}</text>'
        y_offset += 50 + len(items)*26 + 18

    svg += '</svg>'
    with open(os.path.join(OUT, "9_security_arch.svg"), "w", encoding="utf-8") as f:
        f.write(svg)

# ─────────────────────────────────────────────────────────────
# SVG E: MONITORING & AUDIT FLOW — FULL COLOR
# ─────────────────────────────────────────────────────────────
def make_monitoring():
    stages = [
        ("USER ACTION", "process-payment call", "#ff0055"),
        ("API EVENT", "Pydantic-validated payload", "#ff8800"),
        ("AI DECISION", "CatBoost scores 5 actions", "#ffcc00"),
        ("SYSTEM EVENT", "guardrail_triggered · recommended_action", "#aaff00"),
        ("AUDIT LOG INSERT", "RecoveryEvent written to DB", "#00ff88"),
        ("SQLite DATABASE", "recoverai_audit.db", "#00ccff"),
        ("MONITORING DASHBOARD", "/api/recent-events · /api/dashboard-stats", "#aa00ff"),
    ]
    w, h = 960, 120 + len(stages)*110
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%">\n'
    svg += DEFS_BASE
    svg += f'<rect width="{w}" height="{h}" fill="#090a0f" rx="16"/>\n'
    svg += f'<text x="480" y="45" font-family="Consolas,monospace" font-size="22" font-weight="bold" fill="#ffffff" text-anchor="middle" filter="url(#glow2)">📡  MONITORING &amp; AUDIT FLOW</text>\n'

    for i, (name, sub, col) in enumerate(stages):
        y = 100 + i*110
        # Glow dot on left
        svg += f'<circle cx="100" cy="{y}" r="12" fill="{col}" fill-opacity="0.3" stroke="{col}" stroke-width="2" filter="url(#glow)"><animate attributeName="r" from="10" to="14" dur="1.2s" repeatCount="indefinite" values="10;14;10"/></circle>'
        svg += f'<circle cx="100" cy="{y}" r="6" fill="{col}" filter="url(#glow)"/>'
        # Node box
        svg += f'<rect x="140" y="{y-35}" width="760" height="70" rx="10" fill="{col}" fill-opacity="0.1" stroke="{col}" stroke-width="2" filter="url(#glow)"/>'
        svg += f'<text x="170" y="{y-8}" font-family="Consolas,monospace" font-size="15" font-weight="bold" fill="{col}" filter="url(#glow)">{name}</text>'
        svg += f'<text x="170" y="{y+18}" font-family="Consolas,monospace" font-size="12" fill="{col}" fill-opacity="0.75">{sub}</text>'
        # Connector
        if i < len(stages)-1:
            nc = stages[i+1][2]
            svg += dline(100, y+12, 100, y+98, col)
            svg += f'<polygon points="100,{y+98} 93,{y+86} 107,{y+86}" fill="{nc}" filter="url(#glow)"/>'

    svg += '</svg>'
    with open(os.path.join(OUT, "10_monitoring_flow.svg"), "w", encoding="utf-8") as f:
        f.write(svg)

# ─────────────────────────────────────────────────────────────
# SVG F: API ARCHITECTURE — FULL COLOR REQUEST/RESPONSE
# ─────────────────────────────────────────────────────────────
def make_api():
    req_stages = [
        ("CLIENT", "#ff0055"), ("HTTP POST REQUEST", "#ff6600"), ("FASTAPI ROUTER", "#ffcc00"),
        ("PYDANTIC VALIDATION", "#aaff00"), ("BUSINESS LOGIC", "#00ff88"), ("GUARDRAILS ENGINE", "#00ccff"),
        ("CATBOOST INFERENCE", "#0088ff"), ("DECISION ENGINE", "#4400ff"), ("AUDIT DATABASE", "#aa00ff"),
        ("JSON RESPONSE ←", "#ff00ff"),
    ]
    w, h = 960, 120 + len(req_stages)*95
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%">\n'
    svg += DEFS_BASE
    svg += f'<rect width="{w}" height="{h}" fill="#090a0f" rx="16"/>\n'
    svg += f'<text x="480" y="45" font-family="Consolas,monospace" font-size="22" font-weight="bold" fill="#ffffff" text-anchor="middle" filter="url(#glow2)">🌐  API ARCHITECTURE</text>\n'

    for i, (name, col) in enumerate(req_stages):
        y = 100 + i*95
        # Left: request flow (downward)
        svg += f'<rect x="60" y="{y}" width="380" height="60" rx="10" fill="{col}" fill-opacity="0.12" stroke="{col}" stroke-width="2" filter="url(#glow)"/>'
        svg += f'<text x="250" y="{y+35}" font-family="Consolas,monospace" font-size="14" font-weight="bold" fill="{col}" text-anchor="middle" filter="url(#glow)">{name}</text>'
        if i < len(req_stages)-1:
            nc = req_stages[i+1][1]
            svg += arrow_down(250, y+60, y+95, nc)

    # Response labels on right
    resp = [
        "← HTTP/1.1 200 OK",
        "← RecoveryDecision JSON",
        "← Validated payload",
        "← Serialized response",
        "← Decision made",
        "← Action confirmed",
        "← Probability scores",
        "← recommended_action",
        "← Event logged",
        "",
    ]
    resp_col = ["#ff00ff","#ff0099","#ff0055","#ff4400","#ff8800","#ffcc00","#aaff00","#00ff88","#00ccff",""]
    for i, (r, rc) in enumerate(zip(resp, resp_col)):
        if r:
            y = 100 + i*95 + 30
            svg += f'<text x="520" y="{y}" font-family="Consolas,monospace" font-size="12" fill="{rc}" filter="url(#glow)">{r}</text>'

    svg += '</svg>'
    with open(os.path.join(OUT, "7_api_arch.svg"), "w", encoding="utf-8") as f:
        f.write(svg)

# Run all
make_guardrails()
make_ml_pipeline()
make_arch()
make_security()
make_monitoring()
make_api()

print("All colorful SVGs generated!")
