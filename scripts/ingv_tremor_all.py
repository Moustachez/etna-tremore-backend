from obspy.clients.fdsn import Client
from obspy import UTCDateTime
import numpy as np
from scipy.signal import butter, filtfilt
import json
import os
from datetime import datetime, timezone, timedelta

# ============================
# CONFIGURAZIONE
# ============================
STATIONS = ["ECNE", "ECPN", "ECBD", "EMFS"]
NETWORK = "IV"
CHANNEL = "HHZ"
DURATION = 300  # 5 minuti: finestra totale scaricata ad ogni esecuzione
SUBWINDOW_SECONDS = 30  # dimensione di ogni "fetta" per il calcolo RMS
GAIN_MV_PER_COUNT = 0.000643915  # mV per count (uguale per tutte)
THRESHOLDS = {
    "quiet_max": 1.0,
    "moderate_max": 9.0
}
# 24 ore di storico a risoluzione 30s: 24*3600/30 = 2880 punti per stazione
MAX_HISTORY_POINTS = 2880


def butter_bandpass(lowcut, highcut, fs, order=4):
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype='band')
    return b, a


def apply_filter(data, fs, lowcut=0.5, highcut=5.0):
    b, a = butter_bandpass(lowcut, highcut, fs)
    return filtfilt(b, a, data)


def classify(rms_mV):
    if rms_mV <= THRESHOLDS["quiet_max"]:
        return "QUIETE", "Quiete", "#22c55e"
    elif rms_mV <= THRESHOLDS["moderate_max"]:
        return "MODERATO", "Attività moderata", "#eab308"
    else:
        return "ALTO", "Attività elevata", "#ef4444"


def process_station(station):
    """
    Scarica i 300s di segnale della stazione e li divide in "fette" da
    SUBWINDOW_SECONDS ciascuna, calcolando un RMS per ogni fetta invece che
    una sola media su tutta la finestra. Così i picchi brevi (pochi secondi)
    restano visibili come punte isolate, invece di sparire nella media.
    Restituisce una lista di letture (una per fetta), non un singolo valore.
    """
    print(f"   📡 {station}...", end=" ")
    client = Client("INGV")
    end = UTCDateTime()
    start = end - DURATION
    try:
        st = client.get_waveforms(NETWORK, station, "", CHANNEL, start, end)
        tr = st[0]
        data = tr.data
        fs = tr.stats.sampling_rate
        trace_start = tr.stats.starttime
        print(f"✅ {len(data)} campioni", end=" ")
    except Exception as e:
        print(f"❌ Errore: {e}")
        return []

    data_filtered = apply_filter(data, fs)

    samples_per_subwindow = int(SUBWINDOW_SECONDS * fs)
    if samples_per_subwindow <= 0:
        print("❌ Campionamento non valido")
        return []

    n_subwindows = len(data_filtered) // samples_per_subwindow
    readings = []

    for i in range(n_subwindows):
        chunk = data_filtered[i * samples_per_subwindow: (i + 1) * samples_per_subwindow]
        rms_counts = np.sqrt(np.mean(chunk ** 2))
        rms_mV = rms_counts * GAIN_MV_PER_COUNT
        level, label, color = classify(rms_mV)
        chunk_time = (trace_start + i * SUBWINDOW_SECONDS).datetime.replace(tzinfo=timezone.utc)
        readings.append({
            "timestamp": chunk_time.isoformat(),
            "rms_counts": round(float(rms_counts), 2),
            "rms_mV": round(float(rms_mV), 4),
            "level": level,
            "label": label,
            "color": color
        })

    if readings:
        last = readings[-1]
        print(f"→ {n_subwindows} punti, ultimo: {last['rms_mV']:.3f} mV ({last['level']})")

    return readings


def save_history(all_readings: dict) -> None:
    """
    Aggiunge TUTTE le letture di questo ciclo (una per fetta da 30s, non
    una sola media) allo storico per-stazione (docs/history.json).
    """
    history_file = "docs/history.json"
    history_data = {}
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r') as f:
                history_data = json.load(f)
        except (json.JSONDecodeError, OSError):
            history_data = {}

    for station, readings in all_readings.items():
        if station not in history_data:
            history_data[station] = []
        history_data[station].extend(readings)
        history_data[station] = history_data[station][-MAX_HISTORY_POINTS:]

    with open(history_file, 'w') as f:
        json.dump(history_data, f, indent=2)
    print(f"💾 Storico salvato in {history_file}")


def compute_all():
    print(f"[{datetime.now(timezone.utc).isoformat()}] 🔍 Scaricamento dati INGV...")
    print(f"   Stazioni: {', '.join(STATIONS)}")
    print(f"   Durata: {DURATION}s, sotto-finestre da {SUBWINDOW_SECONDS}s, Canale: {CHANNEL}")
    print()

    all_readings = {}
    latest_snapshot = {}

    for station in STATIONS:
        readings = process_station(station)
        if readings:
            all_readings[station] = readings
            latest_snapshot[station] = {
                "rms_counts": readings[-1]["rms_counts"],
                "rms_mV": readings[-1]["rms_mV"],
                "level": readings[-1]["level"],
                "label": readings[-1]["label"],
                "color": readings[-1]["color"],
            }

    if not all_readings:
        print("❌ Nessuna stazione ha restituito dati")
        return

    save_history(all_readings)

    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "network": NETWORK,
        "channel": CHANNEL,
        "duration_seconds": DURATION,
        "subwindow_seconds": SUBWINDOW_SECONDS,
        "gain_mV_per_count": GAIN_MV_PER_COUNT,
        "thresholds": THRESHOLDS,
        "stations": latest_snapshot
    }

    os.makedirs("docs", exist_ok=True)
    with open("docs/ingv_all.json", "w") as f:
        json.dump(output, f, indent=2)

    print()
    print(f"💾 Dati salvati in docs/ingv_all.json")
    print("✅ Completato!")


if __name__ == "__main__":
    compute_all()
