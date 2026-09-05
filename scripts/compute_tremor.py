import requests
import json
import re
from datetime import datetime
import os

LEVEL_MAP = {
    0: {"level": "QUIETE", "label": "Quiete", "color": "#22c55e"},
    1: {"level": "MODERATO", "label": "Attività moderata", "color": "#eab308"},
    2: {"level": "ALTO", "label": "Attività elevata", "color": "#ef4444"}
}

def fetch_tremor():
    url = "https://etnamonitor.it/api/status"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    tremor_value = None
    for reason in data.get("reasons", []):
        match = re.search(r'(\d+)\s*nm/s', reason)
        if match:
            tremor_value = int(match.group(1))
            break
    
    if tremor_value is None:
        raise Exception("Valore tremore non trovato")
    
    level_num = data.get("level", 0)
    level_info = LEVEL_MAP.get(level_num, LEVEL_MAP[0])
    
    return {
        "rms": tremor_value,
        "level": level_info["level"],
        "label": level_info["label"],
        "color": level_info["color"],
        "timestamp": data.get("updated_at")
    }

def compute_tremor():
    print("🔍 Download da EtnaMonitor...")
    tremor_data = fetch_tremor()
    
    output = {
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "station": "ECNE",
        "rms": tremor_data["rms"],
        "level": tremor_data["level"],
        "label": tremor_data["label"],
        "color": tremor_data["color"]
    }
    
    history_file = "docs/tremore.json"
    history_data = {"history": []}
    
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            history_data = json.load(f)
    
    history_data["history"].append({
        "timestamp": output["updated_at"],
        "rms": output["rms"],
        "level": output["level"],
        "label": output["label"],
        "color": output["color"]
    })
    
    if len(history_data["history"]) > 1000:
        history_data["history"] = history_data["history"][-1000:]
    
    history_data["latest"] = {
        "rms": output["rms"],
        "level": output["level"],
        "label": output["label"],
        "color": output["color"],
        "timestamp": output["updated_at"]
    }
    
    os.makedirs("docs", exist_ok=True)
    with open(history_file, 'w') as f:
        json.dump(history_data, f, indent=2)
    
    print(f"✅ Dati salvati: {output['rms']} nm/s - {output['level']}")

if __name__ == "__main__":
    compute_tremor()
