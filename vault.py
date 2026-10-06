# ── vault.py ─────────────────────────────────────────────────────────────────
# Collecte des métadonnées du second cerveau pour la page /vault, en lecture seule :
# index SQLite du serveur MCP, journal de ses appels, API Syncthing, git du vault,
# fiches .meta.json de /root/cerveau-brut. Jamais le corps des notes ni les transcriptions.
# Chaque bloc est collecté à part : une source en panne n'empêche pas les autres.
# ─────────────────────────────────────────────────────────────────────────────

import json
import re
import sqlite3
import subprocess
import time
import urllib.request
from collections import Counter
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path

VAULT = Path("/root/vault")
INDEX_DB = Path("/root/mcp-server/data/index.sqlite")
MCP_LOG = Path("/root/mcp-server/data/mcp-calls.log")
BRUT = Path("/root/cerveau-brut")
BRUT_MAX_OCTETS = 1024 ** 3
MACHINES = ["minipc", "laptop", "pc"]
SYNCTHING_URL = "http://127.0.0.1:8384/rest"
SYNCTHING_CONFIG = Path("/root/.local/state/syncthing/config.xml")
SYNCTHING_FOLDER = "vault"
USAGE_JOURS = 7
LOG_MAX_OCTETS = 4 * 1024 * 1024
A_COMPLETER = "à compléter"


def bloc(fonction, *args):
    try:
        return fonction(*args)
    except Exception as e:
        return {"erreur": f"{type(e).__name__}: {e}"}


def index_db():
    return sqlite3.connect(f"file:{INDEX_DB}?mode=ro", uri=True, timeout=3)


def iso(ts: float) -> str:
    """Horodatage avec fuseau : le LXC est en UTC, le navigateur convertit en heure locale."""
    return datetime.fromtimestamp(ts).astimezone().isoformat(timespec="seconds")


def dernier_rapport() -> date | None:
    dates = []
    for f in (VAULT / "rapports").glob("*.md"):
        try:
            dates.append(date.fromisoformat(f.stem[:10]))
        except ValueError:
            pass
    return max(dates, default=None)


def etat_actuel(chemin: Path) -> str:
    """Première ligne de la section « État actuel » d'un hub (sans le tiret)."""
    dedans = False
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        if ligne.startswith("## "):
            if dedans:
                break
            dedans = ligne.strip() == "## État actuel"
        elif dedans and ligne.strip():
            texte = re.sub(r"\[\[([^|\]]+\|)?([^\]]+)\]\]", r"\2", ligne.strip().lstrip("-* ").strip())
            return texte[:160] + ("…" if len(texte) > 160 else "")
    return ""


# ── Blocs ────────────────────────────────────────────────────────────────────

def contenu():
    with closing(index_db()) as db:
        types = dict(db.execute("SELECT type, COUNT(*) FROM notes GROUP BY type ORDER BY COUNT(*) DESC"))
        total = sum(types.values())
        liens = db.execute("SELECT COUNT(*) FROM liens WHERE cible IS NOT NULL").fetchone()[0]
        casses = db.execute(
            """SELECT COUNT(*) FROM liens l JOIN notes n ON n.path = l.source
               WHERE l.cible IS NULL AND n.type_dossier != 'modele'""").fetchone()[0]
        erreurs = db.execute("SELECT COUNT(*) FROM notes WHERE erreur IS NOT NULL").fetchone()[0]
        orphelines = db.execute(
            """SELECT COUNT(*) FROM notes n WHERE n.type NOT IN ('index', 'contexte', 'modele')
               AND NOT EXISTS (SELECT 1 FROM liens l WHERE l.cible = n.path)
               AND NOT EXISTS (SELECT 1 FROM liens l WHERE l.source = n.path AND l.cible IS NOT NULL)""").fetchone()[0]
        semaine = (date.today() - timedelta(days=7)).isoformat()
        sessions_7j = db.execute("SELECT COUNT(*) FROM notes WHERE type = 'session' AND updated >= ?",
                                 (semaine,)).fetchone()[0]
        projets_actifs = db.execute(
            "SELECT COUNT(*) FROM notes WHERE type = 'projet' AND status = 'actif'").fetchone()[0]
    return {"total": total, "types": types, "liens": liens, "liens_casses": casses, "erreurs": erreurs,
            "orphelines": orphelines, "sessions_7j": sessions_7j, "projets_actifs": projets_actifs,
            "indexe_le": iso(INDEX_DB.stat().st_mtime)}


def projets():
    with closing(index_db()) as db:
        rows = db.execute("SELECT path, nom, title, status, updated, summary FROM notes "
                          "WHERE type = 'projet' ORDER BY updated DESC, nom").fetchall()
    out = []
    for path, nom, titre, statut, maj, resume in rows:
        etat = bloc(etat_actuel, VAULT / path)
        etat = etat if isinstance(etat, str) else ""
        out.append({"nom": nom, "titre": titre, "statut": statut, "maj": maj, "etat": etat,
                    "etat_vide": not etat or A_COMPLETER in etat.lower(),
                    "resume_a_completer": A_COMPLETER in (resume or "").lower()})
    return out


def recentes(n=8):
    with closing(index_db()) as db:
        rows = db.execute("SELECT path, title, type, project, mtime_ns FROM notes "
                          "WHERE type != 'index' ORDER BY mtime_ns DESC LIMIT ?", (n,)).fetchall()
    return [{"chemin": p, "titre": t, "type": ty, "projet": pr, "modifie": iso(m / 1e9)} for p, t, ty, pr, m in rows]


def a_trier():
    """Ce qui attend un tri : captures de la boîte de réception, sessions et conversations brutes
    pas encore traitées par RogerLeJardinier, notes à compléter, notes à corriger."""
    captures, fichiers, plus_ancienne = 0, 0, None
    for f in sorted((VAULT / "boite-de-reception").glob("*.md")):
        n = len(re.findall(r"^## \d{2}:\d{2}", f.read_text(encoding="utf-8"), re.M))
        if n:
            captures += n
            fichiers += 1
            plus_ancienne = plus_ancienne or f.stem.removeprefix("capture-")

    rapport = dernier_rapport()
    depuis = datetime.combine(rapport, datetime.min.time()).timestamp() if rapport else 0
    sessions = sum(1 for f in BRUT.glob("claude-code/*/*.meta.json") if f.stat().st_mtime >= depuis)
    conversations = sum(1 for f in BRUT.glob("claude-ai/conversations/*.json") if f.stat().st_mtime >= depuis)
    memoire = sum(1 for f in BRUT.glob("memoire-claude/*") if f.is_file() and f.stat().st_mtime >= depuis)

    with closing(index_db()) as db:
        completer = [r[0] for r in db.execute(
            "SELECT nom FROM notes WHERE lower(summary) LIKE ? ORDER BY nom", (f"%{A_COMPLETER}%",))]
        corriger = [r[0] for r in db.execute("SELECT nom FROM notes WHERE erreur IS NOT NULL ORDER BY nom")]
    return {"captures": captures, "captures_fichiers": fichiers, "captures_plus_ancienne": plus_ancienne,
            "sessions": sessions, "conversations": conversations, "memoire": memoire,
            "depuis_rapport": rapport.isoformat() if rapport else None,
            "a_completer": completer, "a_corriger": corriger}


def usage_mcp():
    """Appels d'outils MCP par jour sur 7 jours, d'après mcp-calls.log (« date heure | outil | … »)."""
    taille = MCP_LOG.stat().st_size
    with open(MCP_LOG, "rb") as f:
        f.seek(max(0, taille - LOG_MAX_OCTETS))
        lignes = f.read().decode("utf-8", errors="replace").splitlines()
    debut = date.today() - timedelta(days=USAGE_JOURS - 1)
    par_jour = Counter()
    outils = Counter()
    refus = 0
    dernier = None
    for ligne in lignes:
        parties = ligne.split(" | ", 2)
        if len(parties) < 2 or not re.fullmatch(r"[a-z_]+", parties[1]):
            continue
        try:
            ts = datetime.strptime(parties[0], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        if ts.date() < debut:
            continue
        if parties[1] == "chemin_refuse":
            refus += 1
            continue
        par_jour[ts.date()] += 1
        outils[parties[1]] += 1
        dernier = ts
    jours = [debut + timedelta(days=i) for i in range(USAGE_JOURS)]
    return {"jours": [j.isoformat() for j in jours], "appels": [par_jour[j] for j in jours],
            "total": sum(outils.values()), "outils": outils.most_common(6), "refus": refus,
            "dernier": dernier.astimezone().isoformat(timespec="seconds") if dernier else None}


def capture():
    machines = {m: {"sessions": 0, "octets": 0, "derniere": None} for m in MACHINES}
    for meta in BRUT.glob("claude-code/*/*.meta.json"):
        m = machines.setdefault(meta.parent.name, {"sessions": 0, "octets": 0, "derniere": None})
        try:
            fiche = json.loads(meta.read_text(encoding="utf-8"))
        except ValueError:
            continue
        m["sessions"] += 1
        m["octets"] += int(fiche.get("octets", 0))
        recu = fiche.get("recu")
        if recu and (m["derniere"] is None or recu > m["derniere"]):
            m["derniere"] = recu
    total = sum(f.stat().st_size for f in BRUT.rglob("*") if f.is_file())
    etat_ai = BRUT / "claude-ai" / ".etat.json"
    return {"machines": [{"nom": k, **v} for k, v in machines.items()],
            "brut_octets": total, "brut_max": BRUT_MAX_OCTETS,
            "claude_ai_conversations": sum(1 for _ in BRUT.glob("claude-ai/conversations/*.json")),
            "claude_ai_import": iso(etat_ai.stat().st_mtime) if etat_ai.exists() else None}


def syncthing():
    cle = re.search(r"<apikey>([^<]+)</apikey>", SYNCTHING_CONFIG.read_text(encoding="utf-8")).group(1)

    def api(chemin):
        req = urllib.request.Request(f"{SYNCTHING_URL}/{chemin}", headers={"X-API-Key": cle})
        with urllib.request.urlopen(req, timeout=3) as r:
            return json.load(r)

    statut = api(f"db/status?folder={SYNCTHING_FOLDER}")
    dossier = next(f for f in api("config/folders") if f["id"] == SYNCTHING_FOLDER)
    noms = {d["deviceID"]: d["name"] for d in api("config/devices")}
    connexions = api("system/connections")["connections"]
    vus = api("stats/device")
    appareils = [{"nom": noms.get(d["deviceID"], d["deviceID"][:7]),
                  "connecte": connexions.get(d["deviceID"], {}).get("connected", False),
                  "vu": vus.get(d["deviceID"], {}).get("lastSeen")}
                 for d in dossier["devices"] if d["deviceID"] in connexions]
    return {"etat": statut.get("state"), "erreurs": statut.get("errors", 0) + statut.get("pullErrors", 0),
            "a_recevoir": statut.get("needTotalItems", 0), "fichiers": statut.get("localFiles"),
            "appareils": appareils}


def git():
    def g(*args):
        return subprocess.run(["git", "-C", str(VAULT), *args], capture_output=True, text=True,
                              timeout=5, check=True).stdout.strip()
    horodatage, sujet = g("log", "-1", "--format=%cI%x09%s").split("\t", 1)
    try:
        non_pousses = int(g("rev-list", "--count", "@{u}..HEAD"))
    except subprocess.CalledProcessError:
        non_pousses = None
    return {"dernier_commit": horodatage, "sujet": sujet[:120], "non_pousses": non_pousses,
            "non_commites": len([l for l in g("status", "--porcelain").splitlines() if l.strip()])}


def roger():
    rapport = dernier_rapport()
    if not rapport:
        return {"actif": False}
    texte = next((VAULT / "rapports").glob(f"{rapport.isoformat()}*.md")).read_text(encoding="utf-8")
    questions = texte.split("## Questions pour Toma", 1)[1] if "## Questions pour Toma" in texte else ""
    questions = questions.split("\n## ", 1)[0]
    return {"actif": True, "dernier": rapport.isoformat(),
            "questions": len(re.findall(r"^\s*(?:[-*]|\d+\.)\s", questions, re.M))}


# ── Point d'entrée, avec cache ───────────────────────────────────────────────

CACHE_S = 30
_cache = {"ts": 0.0, "donnees": None}


def collecter(statut_service) -> dict:
    if _cache["donnees"] is not None and time.time() - _cache["ts"] < CACHE_S:
        return _cache["donnees"]
    donnees = {
        "mcp": statut_service("mcp-obsidian"),
        "contenu": bloc(contenu),
        "a_trier": bloc(a_trier),
        "projets": bloc(projets),
        "recentes": bloc(recentes),
        "usage": bloc(usage_mcp),
        "capture": bloc(capture),
        "syncthing": bloc(syncthing),
        "git": bloc(git),
        "roger": bloc(roger),
        "genere": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    _cache.update(ts=time.time(), donnees=donnees)
    return donnees
