import os

svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 800" width="100%" height="100%">
  <defs>
    <!-- Gradients for Nodes -->
    <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#ff0055"/><stop offset="100%" stop-color="#ff0000"/></linearGradient>
    <linearGradient id="grad2" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#ff5500"/><stop offset="100%" stop-color="#ff3300"/></linearGradient>
    <linearGradient id="grad3" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#ffaa00"/><stop offset="100%" stop-color="#ff8800"/></linearGradient>
    <linearGradient id="grad4" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#ddcc00"/><stop offset="100%" stop-color="#bbbb00"/></linearGradient>
    <linearGradient id="grad5" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#88dd00"/><stop offset="100%" stop-color="#55cc00"/></linearGradient>
    <linearGradient id="grad6" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#00dd55"/><stop offset="100%" stop-color="#00aa33"/></linearGradient>
    <linearGradient id="grad7" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#00ddaa"/><stop offset="100%" stop-color="#00aa88"/></linearGradient>
    <linearGradient id="grad8" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#00aadd"/><stop offset="100%" stop-color="#0088cc"/></linearGradient>
    <linearGradient id="grad9" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#0055ff"/><stop offset="100%" stop-color="#0000ff"/></linearGradient>
    <linearGradient id="grad10" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#5500ff"/><stop offset="100%" stop-color="#3300dd"/></linearGradient>
    <linearGradient id="grad11" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#aa00ff"/><stop offset="100%" stop-color="#8800dd"/></linearGradient>
    <linearGradient id="grad12" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#ff00ff"/><stop offset="100%" stop-color="#dd00dd"/></linearGradient>
    <linearGradient id="grad13" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#ff00aa"/><stop offset="100%" stop-color="#dd0088"/></linearGradient>
    <linearGradient id="grad14" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#ff5588"/><stop offset="100%" stop-color="#ff3366"/></linearGradient>

    <!-- Glow Filter -->
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="5" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  </defs>

  <!-- Background -->
  <rect width="100%" height="100%" fill="#0d1117" rx="15" />
  
  <g font-family="Arial, sans-serif" font-weight="bold" font-size="12" fill="#ffffff" text-anchor="middle">
"""

stages = [
    "INPUT / DATA", "DATA COLLECTION", "DATASET", "DATA PREPROC.", "FEATURE ENG.",
    "MODEL TRAINING", "MODEL EVAL.", "AI INFERENCE", "GUARDRAILS", "DECISION ENGINE",
    "RECOMMENDATION", "API / BACKEND", "DASHBOARD", "AUDIT LOG"
]

cols = 5
nodes = []

for i, stage in enumerate(stages):
    row = i // cols
    col = i % cols
    if row % 2 == 1:
        col = cols - 1 - col
    
    x = 100 + col * 180
    y = 100 + row * 200
    nodes.append((x, y, stage, f"url(#grad{i+1})"))

# Draw animated path
svg_content += '    <path d="M '
for i, (x, y, _, _) in enumerate(nodes):
    if i == 0:
        svg_content += f"{x},{y} "
    else:
        prev_x, prev_y = nodes[i-1][0], nodes[i-1][1]
        # Smooth curves
        if prev_y == y:
            svg_content += f"L {x},{y} "
        else:
            svg_content += f"Q {prev_x},{y} {x},{y} "

svg_content += '" fill="none" stroke="#444C56" stroke-width="6" />\n'

svg_content += '    <path d="M '
for i, (x, y, _, _) in enumerate(nodes):
    if i == 0:
        svg_content += f"{x},{y} "
    else:
        prev_x, prev_y = nodes[i-1][0], nodes[i-1][1]
        if prev_y == y:
            svg_content += f"L {x},{y} "
        else:
            svg_content += f"Q {prev_x},{y} {x},{y} "

svg_content += '" fill="none" stroke="#58a6ff" stroke-width="4" stroke-dasharray="15, 15">\n'
svg_content += '      <animate attributeName="stroke-dashoffset" from="30" to="0" dur="1s" repeatCount="indefinite" />\n'
svg_content += '    </path>\n'

# Draw Nodes
for x, y, stage, grad in nodes:
    svg_content += f'''
    <g transform="translate({x},{y})">
      <rect x="-70" y="-30" width="140" height="60" rx="10" fill="{grad}" filter="url(#glow)"/>
      <rect x="-70" y="-30" width="140" height="60" rx="10" fill="none" stroke="#ffffff" stroke-width="2" stroke-opacity="0.3"/>
      <text y="5">{stage}</text>
    </g>
    '''

svg_content += """
  </g>
</svg>
"""

os.makedirs(r"C:\Users\nikhi\Downloads\AI-Revenue-recovery-421\assets", exist_ok=True)
with open(r"C:\Users\nikhi\Downloads\AI-Revenue-recovery-421\assets\workflow.svg", "w") as f:
    f.write(svg_content)
