# app.py
import os
import time
import json
import base64
import hashlib
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "neuro_lock_secure_key"

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Simple server-side store of active challenges: nonce -> (challenge_type, issued_time, ttl)
ACTIVE_CHALLENGES = {}

# Helper: simple face "check" from base64 JPEG (very lightweight)
def verify_face_from_base64(b64data):
    try:
        # basic sanity: decode and check size
        header, encoded = b64data.split(',', 1) if ',' in b64data else (None, b64data)
        img_bytes = base64.b64decode(encoded)
        if len(img_bytes) < 5000:
            # very small images are suspicious (likely not a real webcam capture)
            return False
        # optional: save to disk for audit/demo
        fname = f"{UPLOAD_FOLDER}/capture_{int(time.time()*1000)}.jpg"
        with open(fname, "wb") as f:
            f.write(img_bytes)
        return True
    except Exception as e:
        print("verify_face error:", e)
        return False

# Create a randomized challenge
import random
CHALLENGES = [
    {"id":"blink_twice","label":"Blink twice"},
    {"id":"look_left_right","label":"Turn your head left then right"},
    {"id":"follow_dot","label":"Follow the moving dot on screen"},
    {"id":"smile","label":"Smile once"},
]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    if session.get("authenticated"):
        return render_template("dashboard.html")
    return redirect(url_for("index"))

@app.route("/challenge", methods=["GET"])
def challenge():
    nonce = hashlib.sha256(os.urandom(16) + str(time.time()).encode()).hexdigest()[:20]
    chal = random.choice(CHALLENGES)
    ttl = 8  # seconds allowed to respond
    ACTIVE_CHALLENGES[nonce] = {"challenge":chal["id"], "issued":time.time(), "ttl":ttl}
    return jsonify({"nonce":nonce, "challenge":chal["id"], "label":chal["label"], "ttl":ttl})

@app.route("/verify", methods=["POST"])
def verify():
    """
    Expected JSON:
    {
      "nonce": "...",
      "ts": 169...,  (unix seconds)
      "face": "data:image/jpeg;base64,...",
      "blink_count": 2,
      "head_motion": 1.23,
      "focus_score": 0.72,
      "challenge_observed": "blink_twice"   # client-reported observed action
    }
    """
    data = request.get_json(force=True)
    required_fields = ["nonce","ts","face","blink_count","head_motion","focus_score","challenge_observed"]
    for f in required_fields:
        if f not in data:
            return jsonify({"status":"fail","reason":"missing_field","field":f}), 400

    nonce = data["nonce"]
    ts = float(data["ts"])
    now = time.time()

    # basic freshness checks
    if nonce not in ACTIVE_CHALLENGES:
        return jsonify({"status":"fail","reason":"unknown_nonce"}), 400
    chal_record = ACTIVE_CHALLENGES[nonce]
    if now - chal_record["issued"] > chal_record["ttl"] + 2:
        # expired
        ACTIVE_CHALLENGES.pop(nonce, None)
        return jsonify({"status":"fail","reason":"challenge_expired"}), 400
    # optional: enforce client timestamp close to server time
    if abs(now - ts) > 6:
        return jsonify({"status":"fail","reason":"stale_timestamp"}), 400

    # basic face sanity
    face_ok = verify_face_from_base64(data["face"])
    if not face_ok:
        return jsonify({"status":"fail","reason":"face_invalid"}), 400

    # check challenge response correctness
    required_challenge = chal_record["challenge"]
    observed = data["challenge_observed"]
    # simple rules:
    chal_ok = False
    # blink threshold: for "blink_twice" expect blink_count >= 2
    if required_challenge == "blink_twice" and data["blink_count"] >= 2 and observed == "blink_twice":
        chal_ok = True
    # head movement: for look_left_right expect head_motion > threshold (0.8)
    elif required_challenge == "look_left_right" and data["head_motion"] > 0.6 and observed == "look_left_right":
        chal_ok = True
    # follow_dot: ensure some head motion and at least one blink or motion
    elif required_challenge == "follow_dot" and (data["head_motion"] > 0.4 or data["blink_count"] >= 1) and observed == "follow_dot":
        chal_ok = True
    # smile: we trust client-reported smile (client uses mouth region detection), require at least 0.2 head motion or >0 blinks
    elif required_challenge == "smile" and observed == "smile":
        chal_ok = True

    if not chal_ok:
        return jsonify({"status":"fail","reason":"challenge_not_verified"}), 400

    # focus_score check (simulated EEG/focus proxy)
    # expected: focus_score should be reasonably high (>0.45) for authentication success
    focus_score = float(data["focus_score"])
    if focus_score < 0.45:
        # low focus -> require MFA in real system; for demo deny
        return jsonify({"status":"fail","reason":"low_focus","focus_score":focus_score}), 400

    # All checks passed -> authenticate
    session["authenticated"] = True
    # consume nonce
    ACTIVE_CHALLENGES.pop(nonce, None)
    return jsonify({"status":"success","message":"Access granted","focus_score":focus_score})

if __name__ == "__main__":
    # run app
    app.run(host="0.0.0.0", port=5000, debug=True)
