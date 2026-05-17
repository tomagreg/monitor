# ── services.py ──────────────────────────────────────────────────────────────
# Ajoute une entrée ici pour chaque service à surveiller.
# "systemd" = nom exact de l'unité systemd (sans .service)
# ─────────────────────────────────────────────────────────────────────────────

SERVICES = [
    {"name": "BarTracker",   "systemd": "bartracker",   "url": "https://bartrackr.fr", "controllable": True},
    {"name": "Cloudflared",  "systemd": "cloudflared",  "url": None,                   "controllable": False},
    {"name": "Tailscale",    "systemd": "tailscaled",   "url": None,                   "controllable": False},
    {"name": "MCP Obsidian", "systemd": "mcp-obsidian", "url": None,                   "controllable": True},
]
