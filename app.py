from flask import Flask, request, jsonify, render_template_string
from collections import deque
from datetime import datetime, timezone
import os

app = Flask(__name__)

# Keep up to N most recent requests in memory
MAX_LOG = int(os.getenv("MAX_LOG", "1000"))
req_log = deque(maxlen=MAX_LOG)

def client_ip():
    # Respect X-Forwarded-For added by the Codespaces proxy (if present)
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.remote_addr

@app.before_request
def log_request():
    body = request.get_data(cache=True)  # Keep cached so handlers can still read it
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "method": request.method,
        "path": request.path,
        "query": request.query_string.decode("utf-8", errors="replace"),
        "ip": client_ip(),
        "ua": request.headers.get("User-Agent", ""),
        "headers": {k: v for k, v in request.headers.items()},
        "body_bytes": len(body) if body else 0,
    }
    req_log.appendleft(entry)

@app.route("/", methods=["GET"])
def home():
    html = """<!doctype html>
<html><head>
<meta charset="utf-8">
<title>Request Sniffer</title>
<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Noto Sans,sans-serif;margin:20px;}
table{border-collapse:collapse;width:100%} th,td{border:1px solid #ddd;padding:8px;font-size:13px;vertical-align:top;}
tr:nth-child(even){background:#f9f9f9} code{white-space:pre-wrap;word-break:break-all;}
.badge{background:#eef;padding:2px 6px;border-radius:4px} .small{font-size:12px;color:#666}
</style>
<script>
async function refresh(){
  const r = await fetch('/events.json');
  const data = await r.json();
  const tbody = document.getElementById('tbody');
  tbody.innerHTML = '';
  for (const e of data){
    const row = document.createElement('tr');
    row.innerHTML = `
      <td><div><strong>${e.method}</strong> <span class="badge">${e.path}</span></div>
          <div class="small">${e.query||''}</div></td>
      <td><div>${e.ts}</div></td>
      <td><div>${e.ip}</div><div class="small">${e.ua}</div></td>
      <td><code>${JSON.stringify(e.headers, null, 2)}</code></td>
      <td>${e.body_bytes}</td>`;
    tbody.appendChild(row);
  }
}
setInterval(refresh, 2000);
window.onload = refresh;
</script>
</head>
<body>
  <h1>Request Sniffer <span class="badge">max {{max_log}} entries</span></h1>
  <p>Share this page’s URL with any client you want to test. Every HTTP request to <code>{{host_hint}}</code> will show up below.</p>
  <p>
    <form method="post" action="/clear" onsubmit="return confirm('Clear the log?');">
      <button>Clear log</button>
    </form>
    <a href="/healthz">/healthz</a>
  </p>
  <table>
    <thead>
      <tr><th>Request</th><th>Time (UTC)</th><th>Source</th><th>Headers</th><th>Body bytes</th></tr>
    </thead>
    <tbody id="tbody"></tbody>
  </table>
</body></html>"""
    return render_template_string(html, max_log=MAX_LOG, host_hint=request.host_url)

@app.route("/events.json", methods=["GET"])
def events_json():
    return jsonify(list(req_log))

@app.route("/healthz", methods=["GET"])
def health():
    return "ok", 200

@app.route("/clear", methods=["POST"])
def clear():
    req_log.clear()
    return "cleared", 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
