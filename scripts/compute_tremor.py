"""
Calcola il tremore vulcanico dell'Etna a partire dalle forme d'onda sismiche
grezze pubblicate dall'INGV (rete IV), e salva il risultato in un file JSON
che viene pubblicato su GitHub Pages.

Metodo: per ciascuna stazione (in ordine di priorità), scarica gli ultimi
`WINDOW_MINUTES` minuti di segnale sul canale verticale, rimuove la risposta
strumentale per ottenere la velocità del suolo in m/s, e calcola il valore
RMS (Root Mean Square) in nm/s — lo stesso tipo di misura usata nei bollettini
INGV per il tremore vulcanico.

Se una stazione non ha dati disponibili (manutenzione, guasto, ecc.) si passa
automaticamente alla successiva della lista.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from obspy.clients.fdsn import Client
from obspy import UTCDateTime
import numpy as np

# Stazioni della rete IV usate storicamente per il tremore vulcanico
# dell'Etna, in ordine di priorità (fonte: bollettini INGV Osservatorio
# Etneo). Se la prima non ha dati disponibili si prova la successiva.
STATIONS = ["ECPN", "ECBD", "ECNE", "EMFS"]
NETWORK = "IV"
CHANNEL = "HHZ"

WINDOW_MINUTES = 10          # finestra di calcolo del RMS
HISTORY_MAX_POINTS = 4320    # 4320 punti * 10 min = 30 giorni di storico

OUTPUT_FILE = Path(__file__).resolve().parent.parent / "docs" / "tremore.json"


def compute_rms_nm_s(client: Client, station: str, end_time: UTCDateTime) -> float | None:
    """Scarica la forma d'onda e restituisce l'RMS in nm/s, o None se fallisce."""
    start_time = end_time - WINDOW_MINUTES * 60

    try:
        inventory = client.get_stations(
            network=NETWORK,
            station=station,
            channel=CHANNEL,
            starttime=start_time,
            endtime=end_time,
            level="response",
        )
        stream = client.get_waveforms(
            network=NETWORK,
            station=station,
            location="*",
            channel=CHANNEL,
            starttime=start_time,
            endtime=end_time,
        )
    except Exception as exc:  # nessun dato per questa stazione in questo momento
        print(f"[{station}] nessun dato disponibile: {exc}")
        return None

    if len(stream) == 0:
        print(f"[{station}] stream vuoto")
        return None

    try:
        stream.merge(method=1, fill_value="interpolate")
        stream.remove_response(inventory=inventory, output="VEL", water_level=60)
        trace = stream[0]
        # Velocità in m/s -> RMS -> nm/s
        rms_m_s = float(np.sqrt(np.mean(trace.data.astype(float) ** 2)))
        rms_nm_s = rms_m_s * 1e6
        return round(rms_nm_s, 2)
    except Exception as exc:
        print(f"[{station}] errore nell'elaborazione: {exc}")
        return None


def load_history() -> list[dict]:
    if OUTPUT_FILE.exists():
        try:
            data = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
            return data.get("history", [])
        except (json.JSONDecodeError, OSError):
            return []
    return []


def compute_adaptive_thresholds(history: list[dict]) -> dict:
    """
    Calcola soglie "Quiete/Moderato/Alto" relative allo storico recente,
    invece di usare numeri fissi indovinati. Usa i percentili 40° e 80°
    degli ultimi valori disponibili (fino a 30 giorni): sotto il 40°
    percentile = quiete, tra il 40° e l'80° = moderato, sopra = alto
    (attività anomala rispetto al periodo osservato).

    Finché non c'è abbastanza storico (meno di 12 punti, ~2 ore), usa una
    soglia di partenza prudente basata sul valore corrente, che verrà
    raffinata automaticamente man mano che si accumulano dati — la
    calibrazione diventa via via più affidabile nell'arco del primo mese.
    """
    values = [point["value_nm_s"] for point in history if point.get("value_nm_s") is not None]

    if len(values) < 12:
        current = values[-1] if values else 500
        return {
            "quiet_max": round(current * 0.5, 1),
            "moderate_max": round(current * 1.5, 1),
            "calibration": "provvisoria (in attesa di più storico)",
        }

    quiet_max = float(np.percentile(values, 40))
    moderate_max = float(np.percentile(values, 80))

    hours = len(values) * WINDOW_MINUTES / 60
    if hours < 48:
        period = f"~{round(hours)}h"
    else:
        period = f"~{round(hours / 24)} giorni"

    return {
        "quiet_max": round(quiet_max, 1),
        "moderate_max": round(moderate_max, 1),
        "calibration": f"adattiva su {len(values)} misurazioni ({period})",
    }


def main() -> int:
    client = Client("INGV")
    end_time = UTCDateTime.now()

    value = None
    used_station = None
    for station in STATIONS:
        value = compute_rms_nm_s(client, station, end_time)
        if value is not None:
            used_station = station
            break

    history = load_history()

    if value is not None:
        history.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "value_nm_s": value,
                "station": used_station,
            }
        )
        # Tiene solo gli ultimi N punti per non far crescere il file all'infinito.
        history = history[-HISTORY_MAX_POINTS:]
    else:
        print("Nessuna stazione disponibile in questo ciclo: non aggiungo un punto.")

    thresholds = compute_adaptive_thresholds(history)

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "unit": "nm/s",
        "latest": history[-1] if history else None,
        "thresholds": thresholds,
        "history": history,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Scritto {OUTPUT_FILE} — ultimo valore: {output['latest']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
