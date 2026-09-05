import requests
import json
import re
from datetime import datetime
import os

# Mappa livelli EtnaMonitor
LEVEL_MAP = {
    0: {"level": "QUIETE", "label": "Quiete", "color": "#22c55e"},
    1: {"level": "MODERATO", "label": "Attività moderata", "color": "#eab308"},
    2: {"level": "ALTO", "label": "Attività elevata", "color": "#ef4444"}
}

def fetch_tremor():
    """Scarica i dati da EtnaMonitor"""
    url = "https://etnamonitor.it/api/status"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    # Estrai il valore numerico da "reasons"
    tremor_value = None
    for reason in data.get("reasons", []):
        match = re.search(r'(\d+)\s*nm/s', reason)
        if match:
            tremor_value = int(match.group(1))
            break
    
    if tremor_value is None:
        raise Exception("Valore tremore non trovato in 'reasons'")
    
    # Prendi il livello da EtnaMonitor
    level_num = data.get("level", 0)
    level_info = LEVEL_MAP.get(level_num, LEVEL_MAP[0])
    
    return {
        "rms": tremor_value,
        "unit": "nm/s",
        "level": level_info["level"],
        "label": level_info["label"],
        "color": level_info["color"],
        "timestamp": data.get("updated_at"),
        "original_level": level_num,
        "original_label": data.get("label"),
        "original_color": data.get("color")
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
    
    # Crea l'output
    output = {
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "station": "ECNE",
        "unit": "nm/s",
        "rms": tremor_data["rms"],
        "level": tremor_data["level"],
        "label": tremor_data["label"],
        "color": tremor_data["color"],
        "source": tremor_data.get("timestamp", "EtnaMonitor"),
        "original_level": tremor_data.get("original_level"),
        "original_label": tremor_data.get("original_label"),
        "original_color": tremor_data.get("original_color")
    }
    
    # Leggi lo storico esistente
    history_file = "docs/tremore.json"
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            try:
                history_data = json.load(f)
            except json.JSONDecodeError:
                history_data = {"history": []}
    else:
        history_data = {"history": []}
    
    # Aggiungi il nuovo valore
    history_data["history"].append({
        "timestamp": output["updated_at"],
        "rms": output["rms"],
        "level": output["level"],
        "label": output["label"],
        "color": output["color"]
    })
    
    # Mantieni solo gli ultimi 1000 valori
    if len(history_data["history"]) > 1000:
        history_data["history"] = history_data["history"][-1000:]
    
    # Aggiorna i valori più recenti
    history_data["latest"] = {
        "rms": output["rms"],
        "level": output["level"],
        "label": output["label"],
        "color": output["color"],
        "timestamp": output["updated_at"]
    }
    
    # Crea la cartella docs se non esiste
    os.makedirs("docs", exist_ok=True)
    
    # Salva il file
    with open(history_file, 'w') as f:
        json.dump(history_data, f, indent=2)
    
    print(f"  → Dati salvati in {history_file}")
    print("✅ Completato!")

if __name__ == "__main__":
    compute_tremor()
