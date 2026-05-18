# ── services.py ──────────────────────────────────────────────────────────────
# Ajoute une entrée ici pour chaque service à surveiller.
# "systemd" = nom exact de l'unité systemd (sans .service)
# ─────────────────────────────────────────────────────────────────────────────

SERVICES = [
    {"name": "BarTracker",   "systemd": "bartracker",   "url": "https://bartrackr.fr", "controllable": True},
    {"name": "Cloudflared",  "systemd": "cloudflared",  "url": None,                   "controllable": False},
    {"name": "Tailscale",    "systemd": "tailscaled",   "url": None,                   "controllable": False},
    {"name": "MCP Obsidian", "systemd": "mcp-obsidian", "url": None,                   "controllable": True},
    {"name": "Postroom Dashboard", "systemd": "postroom-dashboard", "url": "http://100.113.125.27:5002", "controllable": True, "calibrate": True},
]
