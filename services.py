# ── services.py ──────────────────────────────────────────────────────────────
# Ajoute une entrée ici pour chaque service à surveiller.
# "systemd" = nom exact de l'unité systemd (sans .service)
# ─────────────────────────────────────────────────────────────────────────────

SERVICES = [
    {"name": "BarTracker",  "systemd": "bartracker",  "url": "https://bartrackr.fr"},
    {"name": "Cloudflared", "systemd": "cloudflared", "url": None},
    {"name": "Tailscale",   "systemd": "tailscaled",  "url": None},
    {"name": "MCP Obsidian", "systemd": "mcp-obsidian", "url": None},
]
