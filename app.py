from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import psutil
import subprocess
import threading
import time
from services import SERVICES

REPO_DIR = "/home/tomagreg/repos/monitor"

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
            "name":         svc["name"],
            "systemd":      svc["systemd"],
            "status":       get_service_status(svc["systemd"]),
            "url":          svc.get("url"),
            "controllable": svc.get("controllable", False),
            "calibrate":    svc.get("calibrate", False),
        })
    return jsonify(result)


@app.route("/api/update", methods=["POST"])
def api_update():
    try:
        pull = subprocess.run(
            ["git", "pull"],
            capture_output=True, text=True, timeout=30, cwd=REPO_DIR
        )
        if pull.returncode != 0:
            return jsonify({"error": pull.stderr or pull.stdout}), 500
        output = pull.stdout.strip()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    def delayed_restart():
        time.sleep(1.5)
        subprocess.run(["sudo", "systemctl", "restart", "monitor"])

    threading.Thread(target=delayed_restart, daemon=True).start()
    return jsonify({"output": output})


@app.route("/api/services/<unit>/logs")
def api_service_logs(unit):
    known_units = {svc["systemd"] for svc in SERVICES}
    if unit not in known_units:
        return jsonify({"error": "unknown service"}), 404
    n = min(int(request.args.get("n", 60)), 200)
    result = subprocess.run(
        ["journalctl", "-u", unit, "-n", str(n), "--no-pager", "--output=short-iso"],
        capture_output=True, text=True, timeout=5
    )
    return jsonify({"lines": result.stdout.splitlines()})


@app.route("/api/postroom/calibrate", methods=["POST"])
def api_postroom_calibrate():
    try:
        proc = subprocess.Popen(
            ["sudo", "-u", "postroom", "bash", "-c",
             "cd /opt/postroom && .venv/bin/python src/main.py --calibrate"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"pid": proc.pid})


@app.route("/api/services/<unit>/action", methods=["POST"])
def api_service_action(unit):
    known_units = {svc["systemd"] for svc in SERVICES}
    if unit not in known_units:
        return jsonify({"error": "unknown service"}), 404

    action = request.json.get("action") if request.is_json else None
    if action not in ("start", "stop", "restart"):
        return jsonify({"error": "invalid action"}), 400

    try:
        subprocess.run(
            ["sudo", "systemctl", action, unit],
            capture_output=True, text=True, timeout=15, check=True
        )
    except subprocess.CalledProcessError as e:
        return jsonify({"error": e.stderr or e.stdout}), 500

    return jsonify({"status": get_service_status(unit)})


# ── Frontend ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
