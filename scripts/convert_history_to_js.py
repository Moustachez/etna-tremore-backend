import json
import os

def convert_history_to_js():
    # Leggi il file JSON dello storico
    json_file = "docs/ingv_history.json"
    js_file = "docs/storia.js"
    
    if not os.path.exists(json_file):
        print("❌ ingv_history.json non trovato")
        return
    
    # Carica i dati JSON
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Crea il contenuto JS
    js_content = "var storiaData = " + json.dumps(data, indent=2) + ";"
    
    # Scrivi il file JS
    with open(js_file, 'w') as f:
        f.write(js_content)
    
    print(f"✅ Convertito {json_file} → {js_file}")

if __name__ == "__main__":
    convert_history_to_js()
