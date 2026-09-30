# ── services.py ──────────────────────────────────────────────────────────────
# Ajoute une entrée ici pour chaque service à surveiller.
# "systemd" = nom exact de l'unité systemd (sans .service)
# ─────────────────────────────────────────────────────────────────────────────

SERVICES = [
    {"name": "BarTracker",   "systemd": "bartracker",   "url": "https://bartrackr.fr", "controllable": True},
    {"name": "Cloudflared",  "systemd": "cloudflared",  "url": None,                   "controllable": False},
    {"name": "Tailscale",    "systemd": "tailscaled",   "url": None,                   "controllable": False},
    {"name": "MCP Obsidian", "systemd": "mcp-obsidian", "url": None,                   "controllable": True},
    {"name": "Postroom Dashboard", "systemd": "postroom-dashboard", "url": "http://100.67.37.21:5002", "controllable": True},
    {"name": "Shoals",       "systemd": "shoals",       "url": "http://100.67.37.21:5003", "controllable": True},
]

# Proxy de journalisation du LXC llm (Ollama), lu par /api/llm.
LLM_PROXY_URL = "http://100.103.135.111:11435"
