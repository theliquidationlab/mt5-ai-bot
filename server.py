from flask import Flask, request, jsonify
import os, requests

app = Flask(__name__)

# AI provider (Groq) — OpenAI-compatible base URL
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE = "https://api.groq.com/openai/v1/chat/completions"  #  [oai_citation:2‡console.groq.com](https://console.groq.com/docs/api-reference?utm_source=chatgpt.com)

# stores latest TradingView bias/filter
tv_state = {"bias":"NEUTRAL", "allow": True}

@app.post("/tv")
def tv():
    data = request.get_json(force=True, silent=True) or {}
    tv_state["bias"]  = str(data.get("bias","NEUTRAL")).upper()
    tv_state["allow"] = bool(data.get("allow", True))
    return jsonify({"ok": True, "tv_state": tv_state})

@app.post("/decide")
def decide():
    if not GROQ_API_KEY:
        return jsonify({"error":"GROQ_API_KEY not set"}), 500

    payload = request.get_json(force=True, silent=True) or {}
    feat = payload.get("features", {})
    spread = float(payload.get("spread_points", 999999))

    # Hard safety gates
    if not tv_state["allow"]:
        return jsonify({"action":"HOLD","reason":"tv_allow=false"})
    if spread > float(payload.get("max_spread", 2000)):
        return jsonify({"action":"HOLD","reason":"spread_too_wide"})

    # Prompt: keep it constrained and machine-readable
    prompt = {
        "tv_bias": tv_state["bias"],
        "features": feat,
        "rule": "Return ONLY JSON: {\"action\":\"BUY|SELL|HOLD\",\"confidence\":0-1,\"reason\":\"...\"}.",
        "constraints": [
            "Use MT5 features as primary truth; TradingView bias is only a filter.",
            "If not clearly trending, choose HOLD.",
            "Do NOT invent prices. Do NOT include extra text."
        ]
    }

    body = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role":"system","content":"You are a trading decision filter. Output ONLY strict JSON."},
            {"role":"user","content": str(prompt)}
        ],
        "temperature": 0.1,
        "max_tokens": 120
    }

    r = requests.post(
        GROQ_BASE,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type":"application/json"},
        json=body,
        timeout=20
    )
    r.raise_for_status()
    txt = r.json()["choices"][0]["message"]["content"].strip()

    # Railway returns whatever the model returned (must be JSON)
    return app.response_class(txt, mimetype="application/json")

@app.get("/")
def health():
    return "OK"
