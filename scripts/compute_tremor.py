import requests
import json
import numpy as np
from scipy.signal import butter, filtfilt
from datetime import datetime, timedelta
import os

# ============================
# CONFIGURAZIONE
# ============================
STATION = "ECPN"  # Stazione ufficiale per il tremore
COMPONENT = "HHZ"  # Componente verticale (tipicamente la più usata)
SENSITIVITY = 1.0  # Fattore di calibrazione counts → mV (DA VERIFICARE!)
BAND_LOW = 0.5     # Hz (filtro passa-basso)
BAND_HIGH = 5.0    # Hz (filtro passa-alto)

# Soglie in mV (da calibrare)
THRESHOLDS = {
    "quiet_max": 1.5,
    "moderate_max": 3.0
}

# ============================
# FUNZIONI
# ============================

def butter_bandpass(lowcut, highcut, fs, order=4):
    """Crea un filtro passa-banda Butterworth"""
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype='band')
    return b, a

def apply_bandpass_filter(data, fs, lowcut=0.5, highcut=5.0):
    """Applica il filtro passa-banda al segnale"""
    b, a = butter_bandpass(lowcut, highcut, fs)
    return filtfilt(b, a, data)

def calculate_rms(segnale_filtrato):
    """Calcola l'RMS del segnale"""
    return np.sqrt(np.mean(segnale_filtrato**2))

def counts_to_mv(counts, sensitivity):
    """Converte i counts in mV"""
    return counts * sensitivity

def fetch_ingv_data(station, component, duration_minutes=10):
    """
    Scarica i dati sismici dal server INGV.
    DA ADATTARE all'URL reale che stai usando!
    """
    # Esempio: URL fittizio, sostituisci con quello vero
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=duration_minutes)
    
    # Formato: YYYY-MM-DDTHH:MM:SS
    start_str = start_time.strftime("%Y-%m-%dT%H:%M:%S")
    end_str = end_time.strftime("%Y-%m-%dT%H:%M:%S")
    
    # ⚠️ QUESTO URL È UN ESEMPIO! Sostituisci con l'endpoint reale
    url = f"https://webservices.ingv.it/fdsnws/dataselect/1/query?network=IV&station={station}&channel={component}&starttime={start_str}&endtime={end_str}&format=text"
    
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Errore download dati: {response.status_code}")
    
    # Parsing del formato SAC/miniseed (DA ADATTARE al formato reale)
    # Per ora assumiamo dati in formato testo con una colonna di valori
    lines = response.text.strip().split('\n')
    # Salta l'intestazione se presente
    values = []
    for line in lines:
        if line and not line.startswith('#'):
            parts = line.split()
            if len(parts) >= 3:
                # Assumiamo che il terzo campo sia l'ampiezza in counts
                values.append(float(parts[2]))
    
    fs = len(values) / (duration_minutes * 60)  # Frequenza di campionamento stimata
    return np.array(values), fs

def compute_tremor():
    """Funzione principale"""
    try:
        print(f"[{datetime.now()}] Scaricamento dati per {STATION}...")
        
        # 1. Scarica i dati grezzi
        data_counts, fs = fetch_ingv_data(STATION, COMPONENT)
        print(f"  → Scaricati {len(data_counts)} campioni, fs={fs:.2f} Hz")
        
        # 2. Converti in mV (se già in mV, salta questa conversione)
        data_mv = counts_to_mv(data_counts, SENSITIVITY)
        
        # 3. Applica filtro passa-banda (0.5–5 Hz)
        data_filtered = apply_bandpass_filter(data_mv, fs, BAND_LOW, BAND_HIGH)
        print(f"  → Filtro passa-banda applicato ({BAND_LOW}-{BAND_HIGH} Hz)")
        
        # 4. Calcola RMS
        rms_value = calculate_rms(data_filtered)
        print(f"  → RMS calcolato: {rms_value:.3f} mV")
        
        # 5. Determina il livello di attività
        if rms_value <= THRESHOLDS["quiet_max"]:
            level = "QUIETE"
        elif rms_value <= THRESHOLDS["moderate_max"]:
            level = "MODERATO"
        else:
            level = "ALTO"
        
        print(f"  → Livello: {level}")
        
        # 6. Salva i risultati
        output = {
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "station": STATION,
            "component": COMPONENT,
            "unit": "mV",
            "rms": round(rms_value, 3),
            "level": level,
            "thresholds": THRESHOLDS
        }
        
        # 7. Leggi lo storico esistente
        history_file = "docs/tremore.json"
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                history_data = json.load(f)
        else:
            history_data = {"history": []}
        
        # 8. Aggiungi il nuovo valore
        history_data["history"].append({
            "timestamp": output["updated_at"],
            "rms": output["rms"],
            "level": output["level"]
        })
        
        # 9. Mantieni solo gli ultimi 1000 valori (per non far crescere troppo il file)
        if len(history_data["history"]) > 1000:
            history_data["history"] = history_data["history"][-1000:]
        
        # 10. Aggiorna il file
        with open(history_file, 'w') as f:
            json.dump(history_data, f, indent=2)
        
        print(f"  → Dati salvati in {history_file}")
        print("✅ Completato!\n")
        
    except Exception as e:
        print(f"❌ ERRORE: {e}")

if __name__ == "__main__":
    compute_tremor()
