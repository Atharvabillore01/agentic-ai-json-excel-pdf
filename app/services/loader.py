from pathlib import Path
import pandas as pd, json, uuid, pdfplumber
from app.core.cache import cache

BASE = Path("app/data/states")

def load_state(state_dir: Path):
    state = state_dir.name
    cache["states"][state] = {
        "parks": [],
        "plots": [],
        "pois": [],
        "policy_chunks": []
    }

    for file in state_dir.glob("*.xlsx"):
        xls = pd.ExcelFile(file)
        for sheet in xls.sheet_names:
            df = xls.parse(sheet)
            cols = [c.lower() for c in df.columns]
            if "plotno" in cols:
                cache["states"][state]["plots"] += df.to_dict("records")
            if "park_name" in cols:
                cache["states"][state]["parks"] += df.to_dict("records")

    for file in state_dir.glob("*.json"):
        raw = json.loads(file.read_text())
        feats = raw if isinstance(raw, list) else raw.get("features", [])
        cache["states"][state]["pois"] += feats

    for file in state_dir.glob("*.pdf"):
        with pdfplumber.open(file) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    cache["states"][state]["policy_chunks"].append({
                        "id": str(uuid.uuid4()),
                        "page": i + 1,
                        "source": file.name,
                        "text": text
                    })

def load_all():
    cache["states"].clear()
    for state_dir in BASE.iterdir():
        if state_dir.is_dir():
            load_state(state_dir)
