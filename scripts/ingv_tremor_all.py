from obspy.clients.fdsn import Client
from obspy import UTCDateTime
import numpy as np
from scipy.signal import butter, filtfilt
import json
import os
from datetime import datetime, timezone

# ============================
# CONFIGURAZIONE
# ============================
STATIONS = ["ECNE", "ECPN", "ECBD", "EMFS"]
NETWORK = "IV"
CHANNEL = "HHZ"
DURATION = 300  # 5 minuti
GAIN_MV_PER_COUNT = 0.000643915  # mV per count (uguale per tutte)
THRESHOLDS = {
    "quiet_max": 1.0,
    "moderate_max": 9.0
}

def butter_bandpass(lowcut, highcut, fs, order=4):
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype='band')
    return b, a

def apply_filter(data, fs, lowcut=0.5, highcut=5.0):
    b, a = butter_bandpass(lowcut, highcut, fs)
    return filtfilt(b, a, data)

def process_station(station):
    """Scarica e processa i dati di una singola stazione"""
    print(f"   📡 {station}...", end=" ")
    
    client = Client("INGV")
    end = UTCDateTime()
    start = end - DURATION
    
    try:
        st = client.get_waveforms(NETWORK, station, "", CHANNEL, start, end)
        tr = st[0]
        data = tr.data
        fs = tr.stats.sampling_rate
        print(f"✅ {len(data)} campioni", end=" ")
    except Exception as e:
        print(f"❌ Errore: {e}")
        return None
    
    # Filtro
    data_filtered = apply_filter(data, fs)
    
    # RMS in counts
    rms_counts = np.sqrt(np.mean(data_filtered**2))
    
    # Converti in mV
    rms_mV = rms_counts * GAIN_MV_PER_COUNT
    
    # Determina il livello
    if rms_mV <= THRESHOLDS["quiet_max"]:
        level = "QUIETE"
        label = "Quiete"
        color = "#22c55e"
    elif rms_mV <= THRESHOLDS["moderate_max"]:
        level = "MODERATO"
        label = "Attività moderata"
        color = "#eab308"
    else:
        level = "ALTO"
        label = "Attività elevata"
        color = "#ef4444"
    
    print(f"→ {rms_mV:.3f} mV ({level})")
    
    return {
        "rms_counts": round(rms_counts, 2),
        "rms_mV": round(rms_mV, 4),
        "level": level,
        "label": label,
        "color": color
    }

def compute_all():
    print(f"[{datetime.now(timezone.utc).isoformat()}] 🔍 Scaricamento dati INGV...")
    print(f"   Stazioni: {', '.join(STATIONS)}")
    print(f"   Durata: {DURATION}s, Canale: {CHANNEL}")
    print()
    
    results = {}
    for station in STATIONS:
        data = process_station(station)
        if data:
            results[station] = data
    
    if not results:
        print("❌ Nessuna stazione ha restituito dati")
        return
    
    # Prepara output
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "network": NETWORK,
        "channel": CHANNEL,
        "duration_seconds": DURATION,
        "gain_mV_per_count": GAIN_MV_PER_COUNT,
        "thresholds": THRESHOLDS,
        "stations": results
    }
    
    # Salva JSON
    os.makedirs("docs", exist_ok=True)
    with open("docs/ingv_all.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print()
    print(f"💾 Dati salvati in docs/ingv_all.json")
    print("✅ Completato!")

if __name__ == "__main__":
    compute_all()