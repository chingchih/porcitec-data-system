from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import openpyxl, os

app = FastAPI(title="Porcitec Data System")

BASE = Path(__file__).resolve().parent
DATA_FILE = BASE / "data" / "指標數據.xlsx"
templates = Jinja2Templates(directory=BASE / "templates")

LIFF_ID = os.getenv("LIFF_ID", "")

def _safe(v):
    if v is None:
        return 0
    try:
        return float(v)
    except Exception:
        return 0

def load_data():
    wb = openpyxl.load_workbook(DATA_FILE, read_only=True, data_only=True)
    ws = wb["工作表1"]
    rows = list(ws.iter_rows(values_only=True))
    periods = [p for p in rows[0][1:] if p is not None]
    indicators = []
    for r in rows[1:]:
        if not r or not r[0]:
            continue
        indicators.append({
            "name": str(r[0]).strip(),
            "values": [_safe(r[i]) if i < len(r) else 0 for i in range(1, len(rows[0]))],
        })
    return {
        "periods": periods,
        "indicators": indicators,
        "indicator_names": [i["name"] for i in indicators],
    }

CACHE = load_data()

@app.get("/api/periods")
def api_periods():
    return {"periods": CACHE["periods"]}

@app.get("/api/indicators")
def api_indicators():
    return {"indicators": CACHE["indicator_names"]}

@app.get("/api/data")
def api_data(period: str, indicator: str):
    try:
        idx = CACHE["periods"].index(period)
    except ValueError:
        return JSONResponse({"error": "period not found"}, status_code=404)
    meta = next((i for i in CACHE["indicators"] if i["name"] == indicator), None)
    if meta is None:
        return JSONResponse({"error": "indicator not found"}, status_code=404)
    return {"period": period, "indicator": indicator, "value": meta["values"][idx]}

@app.get("/api/all")
def api_all():
    return CACHE

@app.post("/api/reload")
def api_reload():
    global CACHE
    CACHE = load_data()
    return {"status": "reloaded", "periods": len(CACHE["periods"]), "indicators": len(CACHE["indicators"])}

@app.get("/healthz")
def healthz():
    return {"status": "ok", "file": str(DATA_FILE)}

@app.get("/")
def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "liff_id": LIFF_ID})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
