// static/js/brainwave.js
// Client logic: request challenge, capture short window of frames, compute blink_count, head_motion, focus_score,
// then POST to /verify with base64 image and observed challenge label.

let video = null;
let canvas = null;
let ctx = null;
let currentChallenge = null;
let nonce = null;
let captureFPS = 15;

async function initCamera() {
  video = document.querySelector('video');
  canvas = document.createElement('canvas');
  ctx = canvas.getContext('2d');
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
    video.srcObject = stream;
    await video.play();
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    log("Camera started");
  } catch (e) {
    alert("Camera access required for NeuroLock demo.");
    console.error(e);
  }
}

function log(msg) {
  const el = document.getElementById('log');
  if (el) el.innerText = new Date().toISOString() + " | " + msg + "\n" + el.innerText;
}

async function getChallengeFromServer() {
  const r = await fetch('/challenge');
  const j = await r.json();
  currentChallenge = j.challenge;
  nonce = j.nonce;
  document.getElementById('challenge_label').innerText = j.label;
  log("Challenge received: " + j.label);
}

// simple frame differencing based head motion metric
function computeHeadMotion(frames) {
  if (frames.length < 2) return 0;
  let acc = 0;
  for (let i = 1; i < frames.length; i++) {
    const a = frames[i-1].data;
    const b = frames[i].data;
    let diff = 0;
    // sample pixels every N to speed up
    for (let p = 0; p < a.length; p += 40) {
      diff += Math.abs(a[p] - b[p]) + Math.abs(a[p+1] - b[p+1]) + Math.abs(a[p+2] - b[p+2]);
    }
    acc += diff / (a.length / 4);
  }
  return acc / (frames.length - 1);
}

// very simple blink estimator: sample a horizontal band where eyes usually are and check brightness dips
function estimateBlinkCount(frames) {
  if (frames.length === 0) return 0;
  const w = frames[0].width;
  const h = frames[0].height;
  const eyeY = Math.floor(h * 0.28); // approximate eye row
  const window = 6; // sample height
  let vals = [];
  for (let f of frames) {
    let sum = 0, cnt = 0;
    for (let y = eyeY; y < eyeY + window; y++) {
      for (let x = Math.floor(w*0.25); x < Math.floor(w*0.75); x += 4) {
        const idx = (y * w + x) * 4;
        // brightness approx
        sum += (f.data[idx] + f.data[idx+1] + f.data[idx+2]) / 3;
        cnt++;
      }
    }
    vals.push(sum / cnt);
  }
  // detect dips below a dynamic threshold
  let mean = vals.reduce((a,b)=>a+b,0) / vals.length;
  let blinks = 0;
  for (let i = 1; i < vals.length-1; i++) {
    if (vals[i] < mean * 0.88 && vals[i-1] >= mean * 0.88 && vals[i+1] >= mean * 0.88) blinks++;
  }
  return blinks;
}

// focus_score: proxy from green-channel variance (rPPG-like) and blink rate (less blinking -> more focused)
function computeFocusScore(greenSeries, blinkCount, durationSec) {
  if (greenSeries.length === 0) return 0.0;
  const mean = greenSeries.reduce((a,b)=>a+b,0) / greenSeries.length;
  let varSum = greenSeries.reduce((a,b)=>a + Math.pow(b-mean,2),0) / greenSeries.length;
  // normalize variance roughly into 0-1
  let varNorm = Math.tanh(varSum * 10); // heuristic
  // blink influence: fewer blinks -> higher focus; cap blink per second
  let blinkRate = blinkCount / Math.max(0.5, durationSec);
  let blinkScore = Math.max(0, 1 - Math.min(1.5, blinkRate)); // 1 -> calm, 0 -> heavy blinking
  // combine
  let focus = 0.6 * (1 - varNorm) + 0.4 * blinkScore;
  // clamp 0..1
  return Math.max(0, Math.min(1, focus));
}

// capture short window and compute features
async function captureAndCompute(durationSec=4) {
  const fps = captureFPS;
  const total = Math.max(4, Math.floor(durationSec * fps));
  const frames = [];
  const greenSeries = [];
  for (let i = 0; i < total; i++) {
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
    frames.push(img);
    // green channel mean over forehead area
    const fh = Math.floor(canvas.height * 0.13), fy = Math.floor(canvas.height * 0.12), fx1 = Math.floor(canvas.width*0.35), fx2 = Math.floor(canvas.width*0.65);
    let gsum = 0, gcnt = 0;
    for (let y = fy; y < fy+fh; y+=3) {
      for (let x = fx1; x < fx2; x+=3) {
        const idx = (y * canvas.width + x) * 4;
        gsum += img.data[idx+1];
        gcnt++;
      }
    }
    greenSeries.push(gsum / Math.max(1, gcnt) / 255.0);
    await new Promise(r => setTimeout(r, 1000 / fps));
  }
  const blinkCount = estimateBlinkCount(frames);
  const headMotion = computeHeadMotion(frames);
  const focusScore = computeFocusScore(greenSeries, blinkCount, durationSec);
  // produce a representative single frame (middle)
  const repFrame = frames[Math.floor(frames.length/2)];
  // make a small canvas toDataURL of the repFrame
  const smallCanvas = document.createElement('canvas');
  smallCanvas.width = canvas.width;
  smallCanvas.height = canvas.height;
  const scCtx = smallCanvas.getContext('2d');
  scCtx.putImageData(repFrame, 0, 0);
  const b64 = smallCanvas.toDataURL("image/jpeg", 0.7);
  return { b64, blinkCount, headMotion, focusScore };
}

// Main: called by UI when user requests authentication
async function performAuthentication() {
  if (!nonce || !currentChallenge) {
    alert("Get a challenge first.");
    return;
  }
  // show prompt to user visually (already shown in HTML)
  log("Perform the action now: " + document.getElementById('challenge_label').innerText);
  // capture 4 seconds of data
  const startTs = Date.now() / 1000.0;
  const res = await captureAndCompute(4);
  const payload = {
    nonce: nonce,
    ts: startTs,
    face: res.b64,
    blink_count: res.blinkCount,
    head_motion: res.headMotion,
    focus_score: res.focusScore,
    challenge_observed: currentChallenge
  };
  log("Sending features: blink=" + res.blinkCount + " headMotion=" + res.headMotion.toFixed(2) + " focus=" + res.focusScore.toFixed(2));
  const resp = await fetch('/verify', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(payload)
  });
  const jr = await resp.json();
  if (jr.status === "success") {
    log("Authentication success. Redirecting to dashboard...");
    window.location.href = "/dashboard";
  } else {
    log("Auth failed: " + JSON.stringify(jr));
    alert("Authentication failed: " + (jr.reason || jr.message || "unknown"));
  }
}

// wire buttons on DOM ready
window.addEventListener('DOMContentLoaded', () => {
  document.getElementById('getChallengeBtn').addEventListener('click', async () => {
    await getChallengeFromServer();
  });
  document.getElementById('authBtn').addEventListener('click', async () => {
    await performAuthentication();
  });
  initCamera();
});
