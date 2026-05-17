from flask import Flask, jsonify, render_template
from flask_cors import CORS
import psutil
import subprocess
import time
from services import SERVICES

app = Flask(__name__)
CORS(app)

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_cpu_temp():
    """Lit la température CPU du Pi (fichier thermal_zone)."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return round(int(f.read()) / 1000, 1)
    except Exception:
        return None


def get_service_status(unit: str) -> str:
    """Retourne 'active', 'inactive' ou 'failed' pour une unité systemd."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", unit],
            capture_output=True, text=True, timeout=3
        )
        status = result.stdout.strip()
        return status if status in ("active", "inactive", "failed") else "unknown"
    except Exception:
        return "unknown"


# ── Routes API ────────────────────────────────────────────────────────────────

@app.route("/api/system")
def api_system():
    cpu_freq = psutil.cpu_freq()
    disk = psutil.disk_usage("/")
    ram = psutil.virtual_memory()

    return jsonify({
        "cpu": {
            "percent": psutil.cpu_percent(interval=0.5),
            "freq_mhz": round(cpu_freq.current) if cpu_freq else None,
            "temp_c": get_cpu_temp(),
            "cores": psutil.cpu_count(),
        },
        "ram": {
            "percent": ram.percent,
            "used_mb": round(ram.used / 1024 / 1024),
            "total_mb": round(ram.total / 1024 / 1024),
        },
        "disk": {
            "percent": disk.percent,
            "used_gb": round(disk.used / 1024 / 1024 / 1024, 1),
            "total_gb": round(disk.total / 1024 / 1024 / 1024, 1),
        },
        "uptime_s": int(time.time() - psutil.boot_time()),
    })


@app.route("/api/services")
def api_services():
    result = []
    for svc in SERVICES:
        result.append({
            "name": svc["name"],
            "systemd": svc["systemd"],
            "status": get_service_status(svc["systemd"]),
            "url": svc.get("url"),
        })
    return jsonify(result)


# ── Frontend ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
