import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from polar_stats import compute_polar_stats

# --- 설정 ---
TARGET_R = float(os.environ.get("TARGET_R", "160"))
SCORE_SLOPE = int(os.environ.get("SCORE_SLOPE", "200"))  # 점수 감산 계수 (작을수록 후함)

# Google Sheets 설정
SHEET_ENABLED = os.environ.get("SHEET_ENABLED", "false").lower() == "true"
SHEET_JSON_PATH = os.environ.get("SHEET_JSON_PATH", "service_account.json")
SHEET_NAME = os.environ.get("SHEET_NAME", "CircleGameLog")
SHEET_WORKSHEET = os.environ.get("SHEET_WORKSHEET", "Sheet1")

gspread = None
Credentials = None
ws = None
if SHEET_ENABLED:
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except Exception as e:
        print("⚠️ gspread 불러오기 실패:", e)

app = Flask(__name__)

def connect_sheet():
    """Google Sheets 연결"""
    global ws
    if not SHEET_ENABLED or gspread is None:
        return None
    scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(SHEET_JSON_PATH, scopes=scopes)
    gc = gspread.authorize(creds)
    try:
        sh = gc.open(SHEET_NAME)
    except gspread.SpreadsheetNotFound:
        sh = gc.create(SHEET_NAME)
    try:
        ws = sh.worksheet(SHEET_WORKSHEET)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=SHEET_WORKSHEET, rows=1000, cols=20)
    if not ws.row_values(1):
        ws.insert_row(["timestamp","score","duration_s","sigma","sigma_rel","num_points","client_w","client_h"], index=1)
    return ws

@app.route("/")
def index():
    return render_template("index.html", target_r=int(TARGET_R))

@app.post("/submit")
def submit():
    data = request.get_json(force=True)
    pts = data.get("points", [])
    cx, cy = float(data["center"]["x"]), float(data["center"]["y"])
    duration_s = float(data.get("duration_s", 0.0))
    cw, ch = data.get("client_w", 0), data.get("client_h", 0)

    stats = compute_polar_stats(pts, cx, cy, TARGET_R)
    sigma_rel = stats["sigma_rel"]
    score = max(0, min(100, int(round(100 - SCORE_SLOPE * sigma_rel))))

    # Google Sheets 기록
    if SHEET_ENABLED and gspread is not None:
        try:
            global ws
            if ws is None:
                ws = connect_sheet()
            ws.append_row([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                score, duration_s, stats["sigma"], sigma_rel, len(pts), cw, ch
            ], value_input_option="USER_ENTERED")
        except Exception as e:
            print("⚠️ Sheets 저장 실패:", e)

    return jsonify({"ok": True, "score": score, "duration_s": duration_s})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
