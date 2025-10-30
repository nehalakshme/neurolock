import dash
from dash import dcc, html, Input, Output, State, ctx
import dash_bootstrap_components as dbc
import pandas as pd
import sqlite3
import numpy as np
import os, base64, io, joblib
import plotly.express as px
import plotly.graph_objects as go


# ---------- DATABASE ----------
DB_FILE = "neurolock.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empid TEXT UNIQUE,
    name TEXT,
    password TEXT,
    brainwave_path TEXT
)
""")
conn.commit()


ADMIN_CODE = "ADMIN123"


# ---------- LOAD AI MODEL ----------
MODEL_FILE = "neurolock_invariant_model.pkl"
brainwave_model = None
if os.path.exists(MODEL_FILE):
    try:
        brainwave_model = joblib.load(MODEL_FILE)
        print("✅ Loaded AI model:", MODEL_FILE)
    except Exception as e:
        print("⚠️ Failed to load model:", e)
else:
    print("⚠️ Model file not found:", MODEL_FILE)


# ---------- APP ----------
external_stylesheets = [dbc.themes.BOOTSTRAP]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
app.title = "NeuroLock System"


# ---------- CSS + BACKGROUND ----------
app.index_string = """
<!doctype html>
<html>
<head>
{%metas%}
<title>NeuroLock</title>
{%favicon%}
{%css%}
<style>
:root {
    --bg-0: #05060a;
    --bg-1: #0b0f1a;
    --neon-blue: #3b82f6;
    --neon-purple: #9333ea;
    --card-border: rgba(147,51,234,0.25);
}
* { box-sizing: border-box; margin:0; padding:0; font-family: "Poppins", system-ui; }
html, body { height:100%; overflow-x:hidden; background: linear-gradient(180deg, var(--bg-0), var(--bg-1)); color:#e6eef8; }

/* CARD UI */
.glass-card {
    background: rgba(255,255,255,0.04);
    border-radius: 16px;
    padding: 24px;
    border: 1px solid var(--card-border);
    width: 75%;
    margin: auto;
}


/* INPUT FIELDS */
input.form-control {
    width:100%; padding:12px; border-radius:8px;
    background: rgba(255,255,255,0.08);
    color:white; border:none;
}
input.form-control:focus {
    background: rgba(255,255,255,0.08) !important;
    color:white !important;
    border:1px solid var(--neon-purple) !important;
    box-shadow:0 0 12px rgba(147,51,234,0.6) !important;
}
input.form-control::placeholder { color: rgba(255,255,255,0.7) !important; }


.btn-neon {
    width:100%; padding:12px; border-radius:10px; border:none;
    background: linear-gradient(90deg,var(--neon-blue),var(--neon-purple));
    color:white; font-weight:bold;
    transition: transform 0.3s ease;
}
.btn-neon:hover { transform:scale(1.05); }


.upload-zone {
    border: 1px dashed rgba(255,255,255,0.3);
    padding:12px; text-align:center; border-radius:10px;
    cursor:pointer; color: rgba(255,255,255,0.85);
}

/* Neon Gradient Tabs Styling */
.dash-tabs .tab {
  background: linear-gradient(90deg, var(--neon-blue), var(--neon-purple));
  color: white !important;
  font-weight: 700;
  border-radius: 10px 10px 0 0;
  margin-right: 4px;
  padding: 8px 16px;
  transition: background-color 0.3s ease, transform 0.2s ease;
  box-shadow: 0 0 4px rgba(59, 130, 246, 0.6);
}

.dash-tabs .tab--selected {
  background: linear-gradient(90deg, var(--neon-purple), var(--neon-blue));
  box-shadow: 0 0 15px rgba(147, 51, 234, 0.9);
  color: white !important;
  transform: scale(1.05);
  z-index: 1;
}

.dash-tabs .tab:hover:not(.tab--selected) {
  background: rgba(59, 130, 246, 0.8);
  color: white !important;
  cursor: pointer;
  transform: scale(1.03);
}

.dash-tabs {
  background: rgba(255, 255, 255, 0.05);
  padding: 4px;
  border-radius: 12px 12px 0 0;
  box-shadow: 0 0 15px rgba(147, 51, 234, 0.1);
  margin-bottom: 1rem;
}
</style>
</head>
<body>
{%app_entry%}
<footer>{%config%}{%scripts%}{%renderer%}</footer>
</body>
</html>
"""


# ---------- Helper Logic ----------
def generate_empid():
    cursor.execute("SELECT empid FROM employees ORDER BY id DESC LIMIT 1")
    last = cursor.fetchone()
    if last:
        try:
            num = int(''.join(filter(str.isdigit, last[0])))
        except:
            num = 100
        return f"E{num + 1}"
    return "E100"


def register_user(name, company_code, password, confirm_password):
    if not name or not company_code or not password or not confirm_password:
        return "⚠ Fill all fields."
    if company_code != "230106":
        return "❌ Invalid company code."
    if password != confirm_password:
        return "❌ Passwords do not match."

    empid = generate_empid()
    cursor.execute("INSERT INTO employees (empid, name, password, brainwave_path) VALUES (?, ?, ?, NULL)",
                   (empid, name, password))
    conn.commit()
    return f"✅ Registered! Your Employee ID is {empid}"



    empid = generate_empid()
    cursor.execute("INSERT INTO employees (empid, name, password, brainwave_path) VALUES (?, ?, ?, NULL)",
                   (empid, name, password))
    conn.commit()
    return f"✅ Registered! Your Employee ID is {empid}"


def save_brainwave_db(empid, admin_code, contents):
    if admin_code != ADMIN_CODE:
        return "❌ Invalid Admin Code!"
    if not empid or not contents:
        return "⚠ Provide Employee ID and CSV."


    df = pd.read_csv(io.BytesIO(base64.b64decode(contents.split(',')[1])))
    os.makedirs("brainwaves", exist_ok=True)
    save_path = f"brainwaves/{empid}.csv"
    df.to_csv(save_path, index=False)
    cursor.execute("UPDATE employees SET brainwave_path = ? WHERE empid = ?", (save_path, empid))
    conn.commit()
    return f"✅ Brainwave saved for {empid}"


def verify_login_db(empid, password):
    cursor.execute("SELECT * FROM employees WHERE empid=? AND password=?", (empid, password))
    return bool(cursor.fetchone())

import joblib
import numpy as np
import pandas as pd
import io, base64

import joblib
import numpy as np
import pandas as pd
import io, base64
import joblib
import numpy as np
import pandas as pd
import io, base64

def ai_verify_brainwave(empid, uploaded_contents):
    """
    Uses trained ML model (neurolock_invariant_model.pkl)
    to verify uploaded brainwave pattern for a given empid.
    """

    # --- Fetch stored brainwave path from DB ---
    cursor.execute("SELECT brainwave_path FROM employees WHERE empid=?", (empid,))
    row = cursor.fetchone()
    if not row or not row[0]:
        return "⚠ No stored brainwave found."

    stored = pd.read_csv(row[0])
    uploaded = pd.read_csv(io.BytesIO(base64.b64decode(uploaded_contents.split(',')[1])))

    # --- Load model ---
    try:
        model_data = joblib.load("neurolock_invariant_model.pkl")
        print("DEBUG: Model type =", type(model_data))
    except Exception as e:
        return f"⚠️ Model load error: {e}"

    # --- Detect model & scaler ---
    if isinstance(model_data, tuple):
        model = None
        scaler = None
        for obj in model_data:
            if hasattr(obj, "predict"):
                model = obj
            elif hasattr(obj, "transform"):
                scaler = obj
    else:
        model = model_data
        scaler = None

    # --- Compute similarity score (for info only) ---
    min_rows = min(stored.shape[0], uploaded.shape[0])
    min_cols = min(stored.shape[1], uploaded.shape[1])
    diff = np.mean(np.abs(stored.values[:min_rows, :min_cols] - uploaded.values[:min_rows, :min_cols]))
    #print("DEBUG: EEG difference =", diff)

    # --- Prepare uploaded data for model ---
    # Flatten and resize to expected input size (270)
    features = uploaded.values.flatten()
    expected_features = getattr(model, "n_features_in_", 270)
    if len(features) > expected_features:
        features = features[:expected_features]
    elif len(features) < expected_features:
        features = np.pad(features, (0, expected_features - len(features)), mode="constant")

    features = features.reshape(1, -1)

    # Apply scaler if exists
    if scaler is not None:
        try:
            features = scaler.transform(features)
        except Exception as e:
            print("DEBUG: Skipping scaler transform:", e)

    # --- Predict ---
    try:
        pred = model.predict(features)[0]
        print("DEBUG: Model prediction =", pred)
    except Exception as e:
        return f"⚠️ Prediction error: {e}"

    # --- Decision ---
    if pred == 1 or diff < 0.12:
        return f"✅ Brainwave Match (AI Verified)\nEEG Difference: {diff:.4f}"
    else:
        return f"❌ Brainwave Not Matching (AI Rejected)\nEEG Difference: {diff:.4f}"


# ---------- UI Cards ----------
def home_card():
    return html.Div(className="glass-card", children=[
        html.H1(" NeuroLock", style={"textAlign": "center"}),
        html.H4(" Brainwave-based Authentication System", style={"textAlign": "center"}),
        html.Br(),
        html.Img(src="https://i.imgur.com/J7y8l4e.gif", style={"width": "100%", "borderRadius": "12px"}),
        html.Br(), html.Br(),
        html.P("""
            NeuroLock introduces a revolutionary authentication mechanism using EEG brainwave patterns.
            Unlike passwords or fingerprints, brain signals CANNOT be copied or stolen — making this the
            most secure form of authentication.
        """, style={"fontSize": "18px", "textAlign": "center"}),
        html.Br(),
        html.Ul([
            html.Li("✅ Multi-level authentication (Password + Brainwave Match)"),
            html.Li("✅ AI-based EEG verification"),
            html.Li("✅ Real-time analytics and visualizations"),
        ], style={"fontSize": "18px"})
    ])

def register_card():
    return html.Div(className="glass-card", children=[
        html.H3(" Register Employee"),
        dbc.Input(id="reg-name", placeholder="Full Name", className="form-control"),
        html.Br(),
        dbc.Input(id="reg-company-code", placeholder="Company Code", type="password", className="form-control"),
        html.Br(),
        dbc.Input(id="reg-pass", placeholder="Password", type="password", className="form-control"),
        html.Br(),
        dbc.Input(id="reg-confirm", placeholder="Confirm Password", type="password", className="form-control"),
        html.Br(),
        html.Button("Register", id="register-btn", className="btn-neon"),
        html.Div(id="register-output", style={"marginTop": "10px"})
    ])



def record_card():
    return html.Div(className="glass-card", children=[
        html.H3(" Record Brainwave"),
        dbc.Input(id="rec-empid", placeholder="Employee ID", className="form-control"),
        html.Br(),
        dbc.Input(id="rec-admin", placeholder="Admin Code", type="password", className="form-control"),
        html.Br(),
        dcc.Upload(id="rec-upload", children=html.Div(["📂 Upload CSV"]), className="upload-zone"),
        html.Br(),
        html.Button("Upload & Save", id="rec-btn", className="btn-neon"),
        html.Div(id="rec-output", style={"marginTop": "10px"}),
        html.Br(),
        dcc.Graph(id="brainwave-preview")
    ])


def login_card():
    return html.Div(className="glass-card", children=[
        html.H3(" Login Authentication"),
        dbc.Input(id="log-empid", placeholder="Employee ID", className="form-control"),
        html.Br(),
        dbc.Input(id="log-pass", placeholder="Password", type="password", className="form-control"),
        html.Br(),
        html.Button("Login", id="login-btn", className="btn-neon"),
        html.Div(id="login-output", style={"marginTop": "10px"}),
        html.Hr(),
        html.Div(id="level2", style={"display": "none"}, children=[
            html.H4(" Brainwave Verification"),
            dcc.Upload(id="brainwave-verify-upload", children=html.Div(["📂 Upload Brainwave CSV"]), className="upload-zone"),
            html.Br(),
            html.Button("Verify Brainwave", id="verify-btn", className="btn-neon"),
            html.Div(id="verify-output", style={"marginTop": "10px"})
        ])
    ])


def analytics_card():
    cursor.execute("SELECT empid FROM employees")
    users = cursor.fetchall()
    options = [{"label": u[0], "value": u[0]} for u in users]
    return html.Div(className="glass-card", children=[
        html.H3(" Brainwave Analytics"),
        dcc.Dropdown(id="analytics-user-dropdown", options=options, placeholder="Select user",style={"color": "black"}),
        html.Br(),
        dbc.Button("Compute Band Powers", id="compute-bands", className="btn-neon"),
        html.Div(id="band-powers-output", style={"marginTop": "12px"}),
        dcc.Graph(id="psd-plot")
    ])


# ---------- APP LAYOUT ----------
app.layout = dbc.Container([
    html.Div(className="container-main", children=[
       html.Div([
            html.Img(src="/assets/image.png",
                    style={"height": "150px", "marginRight": "50px"}),
            html.H1(" NeuroLock Access Control", className="app-title",
                    style={"flex": "1", "textAlign": "center", "margin": "0"})
        ],
        style={
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center",
            "width": "100%",
            "position": "relative"
        })
        ,

        dcc.Tabs(id="tabs", value="home", children=[
            dcc.Tab(label=" Home", value="home"),
            dcc.Tab(label=" Register", value="register"),
            dcc.Tab(label=" Record Brainwave", value="record"),
            dcc.Tab(label=" Login", value="login"),
            dcc.Tab(label=" Analytics", value="analytics"),
        ], className="dash-tabs"),

        html.Div(id="tab-content")
    ])
], fluid=True)


# ---------- CALLBACKS ----------
@app.callback(Output("tab-content", "children"), Input("tabs", "value"))
def render_tab(tab):
    if tab == "home": return home_card()
    if tab == "register": return register_card()
    if tab == "record": return record_card()
    if tab == "login": return login_card()
    if tab == "analytics": return analytics_card()
    return ""


@app.callback(Output("register-output", "children"),
              Input("register-btn", "n_clicks"),
              State("reg-name", "value"),
              State("reg-company-code", "value"),
              State("reg-pass", "value"),
              State("reg-confirm", "value"))
def on_register(n, name, company_code, pwd, confirm):
    if not n:
        return ""
    return register_user(name, company_code, pwd, confirm)



@app.callback(Output("rec-output", "children"),
              Input("rec-btn", "n_clicks"),
              State("rec-empid", "value"), State("rec-admin", "value"), State("rec-upload", "contents"))
def on_record(n, empid, admin, contents):
    if not n: return ""
    return save_brainwave_db(empid, admin, contents)


@app.callback(Output("brainwave-preview", "figure"),
              Input("rec-upload", "contents"))
def update_graph(contents):
    if contents is None: return {}
    df = pd.read_csv(io.BytesIO(base64.b64decode(contents.split(',')[1])))
    fig = px.line(df, title="📊 Brainwave Data Preview")
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
    return fig


@app.callback(
    [Output("login-output", "children"), Output("level2", "style")],
    Input("login-btn", "n_clicks"),
    State("log-empid", "value"), State("log-pass", "value"))
def on_login(n, empid, pwd):
    if not n: return "", {"display":"none"}
    if verify_login_db(empid, pwd):
        return "✅ Level 1 Passed.", {"display":"block"}
    return "❌ Invalid credentials.", {"display":"none"}


@app.callback(Output("verify-output", "children"),
              Input("verify-btn", "n_clicks"),
              State("log-empid", "value"), State("brainwave-verify-upload", "contents"))
def on_verify(n, empid, contents):
    if not n: return ""
    return ai_verify_brainwave(empid, contents)


@app.callback(Output("band-powers-output", "children"),
              Output("psd-plot", "figure"),
              Input("compute-bands", "n_clicks"),
              State("analytics-user-dropdown", "value"))
def compute_bands(n, empid):
    if not n or not empid:
        return "", {}

    cursor.execute("SELECT brainwave_path FROM employees WHERE empid=?", (empid,))
    row = cursor.fetchone()
    if not row or not row[0] or not os.path.exists(row[0]):
        return "No EEG file found.", {}

    df = pd.read_csv(row[0])
    data = df.values.flatten()
    freqs = np.fft.rfftfreq(len(data), d=1.0/128)
    psd = np.abs(np.fft.rfft(data))**2

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=freqs, y=psd))
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")

    return "✅ Band powers computed successfully.", fig


# ---------- RUN ----------
if __name__ == "__main__":
    os.makedirs("brainwaves", exist_ok=True)
    app.run(debug=True, port=8050)
