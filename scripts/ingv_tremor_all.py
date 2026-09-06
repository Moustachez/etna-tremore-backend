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
DURATION = 300
GAIN_MV_PER_COUNT = 0.000643915
THRESHOLDS = {"quiet_max": 1.0, "moderate_max": 9.0}
HISTORY_LIMIT = 500

# ============================
# FUNZIONI
# ============================
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
    data_filtered = apply_filter(data, fs)
    rms_counts = np.sqrt(np.mean(data_filtered**2))
    rms_mV = rms_counts * GAIN_MV_PER_COUNT
    if rms_mV <= THRESHOLDS["quiet_max"]:
        level, label, color = "QUIETE", "Quiete", "#22c55e"
    elif rms_mV <= THRESHOLDS["moderate_max"]:
        level, label, color = "MODERATO", "Attività moderata", "#eab308"
    else:
        level, label, color = "ALTO", "Attività elevata", "#ef4444"
    print(f"→ {rms_mV:.4f} mV ({level})")
    return {"rms_counts": round(rms_counts, 2), "rms_mV": round(rms_mV, 4),
            "level": level, "label": label, "color": color}

def compute_all():
    timestamp = datetime.now(timezone.utc).isoformat()
    print(f"[{timestamp}] 🔍 Scaricamento dati INGV...")
    print(f"   Stazioni: {', '.join(STATIONS)}")
    print(f"   Durata: {DURATION}s, Canale: {CHANNEL}\n")
    results = {}
    for station in STATIONS:
        data = process_station(station)
        if data:
            results[station] = data
    if not results:
        print("❌ Nessuna stazione ha restituito dati")
        return

    # === NUOVA PARTE: SALVA STORICO ===
    history_file = "docs/history.json"
    history_data = {}
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            try:
                history_data = json.load(f)
            except:
                history_data = {}

    for station, data in results.items():
        if station not in history_data:
            history_data[station] = []
        history_data[station].append({
            "timestamp": timestamp,
            "rms_mV": data["rms_mV"],
            "level": data["level"],
            "label": data["label"],
            "color": data["color"]
        })
        if len(history_data[station]) > HISTORY_LIMIT:
            history_data[station] = history_data[station][-HISTORY_LIMIT:]

    with open(history_file, 'w') as f:
        json.dump(history_data, f, indent=2)
    print(f"   💾 Storico salvato in {history_file}")

    # === SALVA DATI RECENTI ===
    output = {
        "timestamp": timestamp,
        "network": NETWORK,
        "channel": CHANNEL,
        "duration_seconds": DURATION,
        "gain_mV_per_count": GAIN_MV_PER_COUNT,
        "thresholds": THRESHOLDS,
        "stations": results
    }
    with open("docs/ingv_all.json", 'w') as f:
        json.dump(output, f, indent=2)
    print(f"   💾 Dati recenti salvati in docs/ingv_all.json")
    print("✅ Completato!")

if __name__ == "__main__":
    compute_all()
