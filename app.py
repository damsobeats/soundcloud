import json
import os
import urllib.parse
import urllib.request
from flask import Flask, jsonify, request
from soundcloud import SoundCloud

app = Flask(__name__)

# Gestion native des en-têtes CORS sans paquet externe
@app.after_request
def add_cors_headers(response):
  response.headers["Access-Control-Allow-Origin"] = "*"
  response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
  response.headers["Access-Control-Allow-Headers"] = "Content-Type"
  return response

sc = SoundCloud()

def fetch_waveform_samples(track_url):
  if track_url.endswith(".png"):
    track_url = track_url.replace(".png", ".json")

  req = urllib.request.Request(
      track_url, headers={"User-Agent": "Mozilla/5.0"}
  )
  with urllib.request.urlopen(req, timeout=10) as resp:
    data = json.loads(resp.read().decode())
  return data.get("samples", [])

def resample_bars(samples, target_bars=500):
  if not samples:
    return [0.1] * target_bars

  chunk_size = len(samples) / target_bars
  bars = []
  for i in range(target_bars):
    start = int(i * chunk_size)
    end = int((i + 1) * chunk_size)
    chunk = samples[start:end]
    avg = sum(chunk) / len(chunk) if chunk else 0
    bars.append(avg)

  max_val = max(bars) if max(bars) > 0 else 1.0
  return [max(0.04, round((val / max_val) * 1.0, 4)) for val in bars]

@app.route("/api/waveform", methods=["GET", "OPTIONS"])
def get_waveform():
  if request.method == "OPTIONS":
    return "", 204

  artist = request.args.get("artist", "").strip()
  title = request.args.get("title", "").strip()

  if not title:
    return jsonify({"erreur": "Paramètre titre manquant"}), 400

  query = f"{artist} {title}".strip()

  try:
    search_results = list(sc.search_tracks(query, limit=3))
    if not search_results:
      return (
          jsonify({"erreur": "Morceau non trouvé dans la base SoundCloud"}),
          404,
      )

    waveform_url = None
    for track in search_results:
      if getattr(track, "waveform_url", None):
        waveform_url = track.waveform_url
        break

    if not waveform_url:
      return jsonify({"erreur": "Données d'onde indisponibles"}), 404

    raw_samples = fetch_waveform_samples(waveform_url)
    bars = resample_bars(raw_samples, target_bars=500)

    return jsonify({"status": "success", "query": query, "bars": bars})

  except Exception as e:
    return jsonify({"erreur": str(e)}), 500

@app.route("/", methods=["GET"])
def health():
  return jsonify({"status": "online", "service": "Waveform API Onde d'Art"})

if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
