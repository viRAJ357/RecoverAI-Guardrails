import os
import math

OUT_DIR = r"C:\Users\nikhi\Downloads\AI-Revenue-recovery-421\assets"
os.makedirs(OUT_DIR, exist_ok=True)

DEFS = """
  <defs>
    <linearGradient id="g1" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#ff0055"/><stop offset="100%" stop-color="#ff0000"/></linearGradient>
    <linearGradient id="g2" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#ff5500"/><stop offset="100%" stop-color="#ff3300"/></linearGradient>
    <linearGradient id="g3" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#ffaa00"/><stop offset="100%" stop-color="#ff8800"/></linearGradient>
    <linearGradient id="g4" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#ddcc00"/><stop offset="100%" stop-color="#bbbb00"/></linearGradient>
    <linearGradient id="g5" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#88dd00"/><stop offset="100%" stop-color="#55cc00"/></linearGradient>
    <linearGradient id="g6" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#00dd55"/><stop offset="100%" stop-color="#00aa33"/></linearGradient>
    <linearGradient id="g7" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#00ddaa"/><stop offset="100%" stop-color="#00aa88"/></linearGradient>
    <linearGradient id="g8" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#00aadd"/><stop offset="100%" stop-color="#0088cc"/></linearGradient>
    <linearGradient id="g9" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#0055ff"/><stop offset="100%" stop-color="#0000ff"/></linearGradient>
    <linearGradient id="g10" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#5500ff"/><stop offset="100%" stop-color="#3300dd"/></linearGradient>
    <linearGradient id="g11" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#aa00ff"/><stop offset="100%" stop-color="#8800dd"/></linearGradient>
    <linearGradient id="g12" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#ff00ff"/><stop offset="100%" stop-color="#dd00dd"/></linearGradient>
    <linearGradient id="g13" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#ff00aa"/><stop offset="100%" stop-color="#dd0088"/></linearGradient>
    <linearGradient id="g14" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#ff5588"/><stop offset="100%" stop-color="#ff3366"/></linearGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="6" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
    <filter id="glow-intense" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="10" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#00ffff" />
    </marker>
  </defs>
"""

def generate_svg(filename, stages, cols=4, w=1000, title="WORKFLOW"):
    rows = math.ceil(len(stages) / cols)
    h = 200 + rows * 180
    
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="100%">\n'
    svg += DEFS
    svg += f'<rect width="100%" height="100%" fill="#090a0f" rx="15" />\n'
    
    # Title
    svg += f'<text x="{w/2}" y="50" font-family="Arial" font-size="24" font-weight="bold" fill="#ffffff" text-anchor="middle" filter="url(#glow)">{title}</text>\n'
    
    nodes = []
    for i, stage in enumerate(stages):
        row = i // cols
        col = i % cols
        if row % 2 == 1:
            col = cols - 1 - col
        x = (w / (cols + 1)) * (col + 1)
        y = 120 + row * 160
        grad = f"url(#g{(i % 14) + 1})"
        nodes.append((x, y, stage, grad))

    svg += '<g font-family="Arial, sans-serif" font-weight="bold" font-size="12" fill="#ffffff" text-anchor="middle">\n'
    
    # Paths
    path_d = "M "
    for i, (x, y, _, _) in enumerate(nodes):
        if i == 0:
            path_d += f"{x},{y} "
        else:
            px, py = nodes[i-1][0], nodes[i-1][1]
            if py == y:
                path_d += f"L {x},{y} "
            else:
                path_d += f"Q {px},{y} {x},{y} "

    # Static faint line
    svg += f'<path d="{path_d}" fill="none" stroke="#222730" stroke-width="8" />\n'
    
    # Animated glow line
    svg += f'<path d="{path_d}" fill="none" stroke="#00ffff" stroke-width="4" stroke-dasharray="20, 20" filter="url(#glow)">\n'
    svg += '  <animate attributeName="stroke-dashoffset" from="40" to="0" dur="1s" repeatCount="indefinite" />\n'
    svg += '</path>\n'

    # Flowing particles
    svg += f'<path id="animPath_{filename}" d="{path_d}" fill="none" stroke="none" />\n'
    svg += f'''
    <circle r="6" fill="#ffffff" filter="url(#glow-intense)">
      <animateMotion dur="{len(stages)}s" repeatCount="indefinite">
        <mpath href="#animPath_{filename}" />
      </animateMotion>
    </circle>
    '''

    # Nodes
    for x, y, stage, grad in nodes:
        svg += f'''
        <g transform="translate({x},{y})">
          <rect x="-80" y="-35" width="160" height="70" rx="12" fill="{grad}" filter="url(#glow)"/>
          <rect x="-80" y="-35" width="160" height="70" rx="12" fill="none" stroke="#ffffff" stroke-width="2" stroke-opacity="0.5"/>
          <text y="5">{stage}</text>
        </g>
        '''
        
    svg += '</g>\n</svg>'
    
    with open(os.path.join(OUT_DIR, filename + ".svg"), "w") as f:
        f.write(svg)

# 1. Master System Workflow
generate_svg("1_master_workflow", [
    "USER / TXN INPUT", "DATA INGESTION", "DATA VALIDATION", "DATA PREPROC.", 
    "FEATURE ENG.", "ML MODEL", "PREDICTION", "GUARDRAILS ENGINE",
    "DECISION ENGINE", "ACTION RECOMM.", "FASTAPI / BACKEND", "OPERATOR DASHBOARD",
    "AUDIT LOG", "MONITORING"
], cols=4, title="MASTER SYSTEM WORKFLOW")

# 2. Advanced ML Pipeline
generate_svg("2_ml_pipeline", [
    "RAW DATA", "DATA CLEANING", "MISSING VALUE HDL.", "ENCODING", 
    "FEATURE ENG.", "TRAIN / VAL SPLIT", "MODEL TRAINING", "HYPERPARAM OPT.",
    "EARLY STOPPING", "MODEL EVAL.", "MODEL SELECTION", "MODEL SERIALIZATION",
    "INFERENCE", "PREDICTION"
], cols=4, title="ADVANCED ML PIPELINE")

# 5. Real-Time Inference Flow
generate_svg("5_inference_flow", [
    "REQUEST", "API", "VALIDATION", "FEATURE EXTRACT.", 
    "MODEL INFERENCE", "PREDICTION SCORE", "GUARDRAILS", "DECISION ENGINE",
    "RESPONSE", "DASHBOARD"
], cols=4, title="REAL-TIME INFERENCE FLOW")

# 6. Data Flow Architecture
generate_svg("6_data_flow", [
    "DATASET", "PROCESSING", "FEATURE STORE", "MODEL", 
    "PREDICTION", "DECISION", "DATABASE", "DASHBOARD"
], cols=4, title="DATA FLOW ARCHITECTURE")

# 7. API Architecture
generate_svg("7_api_arch", [
    "CLIENT", "HTTP REQUEST", "FASTAPI", "PYDANTIC VAL.", 
    "BUSINESS LOGIC", "GUARDRAILS", "ML INFERENCE", "DECISION ENGINE",
    "AUDIT DATABASE", "JSON RESPONSE"
], cols=4, title="API ARCHITECTURE")

# 8. Dashboard Workflow
generate_svg("8_dashboard_flow", [
    "TRANSACTION", "API", "AI DECISION", "DATABASE", "DASHBOARD"
], cols=5, title="DASHBOARD WORKFLOW")

# 9. Security Architecture
generate_svg("9_security_arch", [
    "USER", "AUTHENTICATION", "AUTHORIZATION", "API", 
    "BUSINESS LOGIC", "DATABASE"
], cols=3, title="SECURITY ARCHITECTURE")

# 10. Monitoring + Audit Flow
generate_svg("10_monitoring_flow", [
    "USER ACTION", "API EVENT", "AI DECISION", "SYSTEM EVENT", 
    "AUDIT LOG", "DATABASE", "MONITORING"
], cols=4, title="MONITORING & AUDIT FLOW")

print("Generated all basic linear SVGs.")

# Custom SVGs for branching/layers

# 3. Layered Architecture
arch_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 900" width="100%" height="100%">
{DEFS}
<rect width="100%" height="100%" fill="#090a0f" rx="15" />
<text x="500" y="50" font-family="Arial" font-size="24" font-weight="bold" fill="#ffffff" text-anchor="middle" filter="url(#glow)">SYSTEM ARCHITECTURE</text>
<g font-family="Arial" font-weight="bold" font-size="16" fill="#ffffff" text-anchor="middle">
'''
layers = [
    ("LAYER 1: USER / OPERATOR", "#ff0055"),
    ("LAYER 2: FRONTEND / OPERATOR DASHBOARD", "#ff5500"),
    ("LAYER 3: API GATEWAY / FASTAPI", "#ffaa00"),
    ("LAYER 4: BUSINESS LOGIC", "#ddcc00"),
    ("LAYER 5: GUARDRAILS ENGINE", "#00dd55"),
    ("LAYER 6: AI / ML INFERENCE ENGINE", "#00aadd"),
    ("LAYER 7: DATABASE / AUDIT TRAIL", "#5500ff"),
    ("LAYER 8: MONITORING / LOGGING", "#ff00ff"),
]
for i, (name, color) in enumerate(layers):
    y = 100 + i * 95
    arch_svg += f'''
    <rect x="150" y="{y}" width="700" height="60" rx="10" fill="{color}" fill-opacity="0.2" stroke="{color}" stroke-width="3" filter="url(#glow)"/>
    <text x="500" y="{y+35}">{name}</text>
    '''
    if i < len(layers) - 1:
        arch_svg += f'''
        <path d="M 500,{y+60} L 500,{y+95}" stroke="#ffffff" stroke-width="4" stroke-dasharray="10,10" opacity="0.7">
            <animate attributeName="stroke-dashoffset" from="20" to="0" dur="1s" repeatCount="indefinite"/>
        </path>
        <path d="M 450,{y+95} L 450,{y+60}" stroke="#00ffff" stroke-width="4" stroke-dasharray="10,10" opacity="0.7">
            <animate attributeName="stroke-dashoffset" from="0" to="20" dur="1s" repeatCount="indefinite"/>
        </path>
        <path d="M 550,{y+60} L 550,{y+95}" stroke="#ff00ff" stroke-width="4" stroke-dasharray="10,10" opacity="0.7">
            <animate attributeName="stroke-dashoffset" from="20" to="0" dur="1s" repeatCount="indefinite"/>
        </path>
        '''
arch_svg += '</g>\n</svg>'
with open(os.path.join(OUT_DIR, "3_system_architecture.svg"), "w") as f:
    f.write(arch_svg)

# 4. Guardrails Safety Workflow (Branching)
guard_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 800" width="100%" height="100%">
{DEFS}
<rect width="100%" height="100%" fill="#090a0f" rx="15" />
<text x="500" y="50" font-family="Arial" font-size="24" font-weight="bold" fill="#ffffff" text-anchor="middle" filter="url(#glow)">GUARDRAILS / AI SAFETY WORKFLOW</text>
<g font-family="Arial" font-weight="bold" font-size="14" fill="#ffffff" text-anchor="middle">

<!-- Paths -->
<path d="M 500,100 L 500,200" stroke="#00ffff" stroke-width="5" stroke-dasharray="15,15"><animate attributeName="stroke-dashoffset" from="30" to="0" dur="1s" repeatCount="indefinite"/></path>
<path d="M 500,260 L 500,360" stroke="#00ffff" stroke-width="5" stroke-dasharray="15,15"><animate attributeName="stroke-dashoffset" from="30" to="0" dur="1s" repeatCount="indefinite"/></path>
<path d="M 500,420 L 300,520" stroke="#00ff00" stroke-width="5" stroke-dasharray="15,15"><animate attributeName="stroke-dashoffset" from="30" to="0" dur="1s" repeatCount="indefinite"/></path>
<path d="M 500,420 L 700,520" stroke="#ff0000" stroke-width="5" stroke-dasharray="15,15"><animate attributeName="stroke-dashoffset" from="30" to="0" dur="1s" repeatCount="indefinite"/></path>
<path d="M 300,580 L 500,680" stroke="#00ff00" stroke-width="5" stroke-dasharray="15,15"><animate attributeName="stroke-dashoffset" from="30" to="0" dur="1s" repeatCount="indefinite"/></path>
<path d="M 700,580 L 500,680" stroke="#ff0000" stroke-width="5" stroke-dasharray="15,15"><animate attributeName="stroke-dashoffset" from="30" to="0" dur="1s" repeatCount="indefinite"/></path>

<!-- Nodes -->
<rect x="400" y="100" width="200" height="60" rx="10" fill="url(#g1)" filter="url(#glow)"/>
<text x="500" y="135">INPUT</text>

<rect x="380" y="200" width="240" height="60" rx="10" fill="url(#g2)" filter="url(#glow)"/>
<text x="500" y="235">RISK CHECK</text>

<rect x="350" y="300" width="300" height="60" rx="10" fill="url(#g3)" filter="url(#glow)"/>
<text x="500" y="335">GUARDRAIL EVALUATION</text>

<polygon points="500,380 580,420 500,460 420,420" fill="url(#g4)" filter="url(#glow)"/>
<text x="500" y="425" fill="#000000">SAFE?</text>

<!-- Branch Labels -->
<text x="380" y="460" fill="#00ff00">YES</text>
<text x="620" y="460" fill="#ff0000">NO</text>

<rect x="200" y="520" width="200" height="60" rx="10" fill="url(#g6)" filter="url(#glow)"/>
<text x="300" y="555">ML / AI POLICY</text>

<rect x="600" y="520" width="200" height="60" rx="10" fill="url(#g14)" filter="url(#glow)"/>
<text x="700" y="555">HUMAN REVIEW</text>

<rect x="400" y="680" width="200" height="60" rx="10" fill="url(#g9)" filter="url(#glow)"/>
<text x="500" y="715">FINAL DECISION</text>

</g>
</svg>
'''
with open(os.path.join(OUT_DIR, "4_guardrails_safety.svg"), "w") as f:
    f.write(guard_svg)

print("Generated custom SVGs.")
