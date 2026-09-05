import requests
import json
import re
from datetime import datetime, timedelta
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
    
    print(f"📡 Dati ricevuti: {json.dumps(data, indent=2)[:500]}...")  # Debug
    
    # Metodo 1: Cerca in "reasons"
    tremor_value = None
    if "reasons" in data and data["reasons"]:
        for reason in data["reasons"]:
            print(f"🔍 Analizzo reason: {reason}")
            match = re.search(r'(\d+)\s*nm/s', reason)
            if match:
                tremor_value = int(match.group(1))
                print(f"✅ Trovato in reasons: {tremor_value}")
                break
    
    # Metodo 2: Se non trovato, cerca in tutto il JSON
    if tremor_value is None:
        print("⚠️ Non trovato in 'reasons', cerco altrove...")
        json_str = json.dumps(data)
        match = re.search(r'(\d+)\s*nm/s', json_str)
        if match:
            tremor_value = int(match.group(1))
            print(f"✅ Trovato nel JSON: {tremor_value}")
    
    if tremor_value is None:
        # Usa un valore di default da EtnaMonitor se disponibile
        if "level" in data:
            print(f"⚠️ Uso il livello come riferimento: {data['level']}")
            # Valori tipici per i livelli EtnaMonitor
            level_defaults = {0: 500, 1: 1500, 2: 3000}
            tremor_value = level_defaults.get(data["level"], 1500)
            print(f"✅ Usato valore di default: {tremor_value}")
        else:
            raise Exception("Valore tremore non trovato in nessun campo")
    
    level_num = data.get("level", 0)
    level_info = LEVEL_MAP.get(level_num, LEVEL_MAP[0])
    
    return {
        "rms": tremor_value,
        "level": level_info["level"],
        "label": level_info["label"],
        "color": level_info["color"],
        "timestamp": data.get("updated_at", datetime.utcnow().isoformat())
    }

def compute_tremor():
    print(f"[{datetime.now()}] 🔍 Download da EtnaMonitor...")
    
    try:
        tremor_data = fetch_tremor()
    except Exception as e:
        print(f"❌ Errore nel download: {e}")
        return
    
    print(f"  → RMS: {tremor_data['rms']} nm/s")
    print(f"  → Livello: {tremor_data['level']} - {tremor_data['label']}")
    print(f"  → Aggiornato: {tremor_data['timestamp']}")
    
    output = {
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "station": "ECNE",
        "rms": tremor_data["rms"],
        "level": tremor_data["level"],
        "label": tremor_data["label"],
        "color": tremor_data["color"],
        "source": "EtnaMonitor"
    }
    
    history_file = "docs/tremore.json"
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            try:
                history_data = json.load(f)
            except:
                history_data = {"history": []}
    else:
        history_data = {"history": []}
    
    # Aggiungi nuovo valore
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
    
    print(f"  → Dati salvati in {history_file}")
    print("✅ Completato!")

if __name__ == "__main__":
    compute_tremor()
