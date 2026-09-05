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
from datetime import datetime, timezone
from pathlib import Path

from obspy.clients.fdsn import Client
from obspy import UTCDateTime
import numpy as np

import matplotlib
matplotlib.use("Agg")  # nessuna interfaccia grafica: gira su server
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Stazioni della rete IV usate storicamente per il tremore vulcanico
# dell'Etna, in ordine di priorità (fonte: bollettini INGV Osservatorio
# Etneo). Se la prima non ha dati disponibili si prova la successiva.
STATIONS = ["ECPN", "ECBD", "ECNE", "EMFS"]
NETWORK = "IV"
CHANNEL = "HHZ"

WINDOW_MINUTES = 10          # finestra di calcolo del RMS
HISTORY_MAX_POINTS = 4320    # 4320 punti * 10 min = 30 giorni di storico

OUTPUT_FILE = Path(__file__).resolve().parent.parent / "docs" / "tremore.json"
CHART_FILE = Path(__file__).resolve().parent.parent / "docs" / "tremore_chart.png"

# Soglie fisse (in migliaia di nm/s) usate sia per l'etichetta testuale sia
# per le bande colorate del grafico. Scelte osservando l'intervallo di valori
# reali registrati durante l'attuale fase attiva dell'Etna: sotto 4.000 nm/s
# = quiete relativa, 4.000-9.000 = moderato, sopra 9.000 = alto.
QUIET_MAX_NM_S = 4000
MODERATE_MAX_NM_S = 9000


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
        trace = stream[0]

        # Controllo di qualità: se la finestra ha troppi dati mancanti
        # (es. per un'interruzione di trasmissione), l'RMS calcolato non è
        # affidabile — può risultare artificialmente altissimo o vicino a
        # zero. Scartiamo e proviamo la stazione successiva.
        expected_samples = WINDOW_MINUTES * 60 * trace.stats.sampling_rate
        completeness = trace.stats.npts / expected_samples if expected_samples > 0 else 0
        if completeness < 0.8:
            print(f"[{station}] dati incompleti ({completeness:.0%}), scarto")
            return None

        stream.remove_response(inventory=inventory, output="VEL", water_level=60)
        trace = stream[0]
        # Velocità in m/s -> RMS -> nm/s
        rms_m_s = float(np.sqrt(np.mean(trace.data.astype(float) ** 2)))
        rms_nm_s = rms_m_s * 1e9

        # Scarta valori fisicamente implausibili (rumore strumentale puro
        # o artefatti di calcolo), invece di pubblicarli come se fossero
        # letture vere.
        if rms_nm_s < 1 or rms_nm_s > 1_000_000:
            print(f"[{station}] valore fuori range plausibile ({rms_nm_s:.2f} nm/s), scarto")
            return None

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


def fixed_thresholds() -> dict:
    """
    Soglie fisse e trasparenti (non "misteriose" come quelle usate
    internamente da INGV, che non sono pubbliche). Coerenti con le bande
    colorate del grafico generato da questo stesso script.
    """
    return {
        "quiet_max": QUIET_MAX_NM_S,
        "moderate_max": MODERATE_MAX_NM_S,
    }


def generate_chart(history: list[dict]) -> None:
    """
    Genera un grafico PNG del tremore, scala logaritmica sull'asse Y,
    con bande colorate: verde sotto 4.000 nm/s, giallo 4.000-9.000,
    rosso sopra 9.000. Salvato in docs/tremore_chart.png e ripubblicato
    ad ogni esecuzione dello script (quindi sempre aggiornato).
    """
    points = [p for p in history if p.get("value_nm_s") is not None]
    if not points:
        print("Nessun dato disponibile: grafico non generato.")
        return

    times = [datetime.fromisoformat(p["timestamp"]) for p in points]
    # Valori in migliaia di nm/s, per leggibilità sull'asse.
    values_k = [p["value_nm_s"] / 1000 for p in points]

    quiet_k = QUIET_MAX_NM_S / 1000
    moderate_k = MODERATE_MAX_NM_S / 1000
    y_min = 0.1
    y_max = max(max(values_k) * 1.3, moderate_k * 1.5)

    fig, ax = plt.subplots(figsize=(10, 4.5))

    ax.axhspan(y_min, quiet_k, color="#a5d6a7", alpha=0.6, zorder=0)      # verde
    ax.axhspan(quiet_k, moderate_k, color="#fff59d", alpha=0.6, zorder=0)  # giallo
    ax.axhspan(moderate_k, y_max, color="#ef9a9a", alpha=0.6, zorder=0)   # rosso

    ax.plot(times, values_k, color="#212121", linewidth=1.1, zorder=2)

    ax.set_yscale("log")
    ax.set_ylim(y_min, y_max)
    ax.set_ylabel("Ampiezza (migliaia di nm/s)")
    ax.set_title("Tremore vulcanico Etna — stazione ECPN")

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m %H:%M"))
    fig.autofmt_xdate()
    ax.grid(True, which="both", axis="y", alpha=0.3)

    fig.tight_layout()
    CHART_FILE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(CHART_FILE, dpi=130)
    plt.close(fig)
    print(f"Scritto {CHART_FILE}")


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
    last_valid_value = next(
        (p["value_nm_s"] for p in reversed(history) if p.get("value_nm_s") is not None), None
    )

    if value is not None and last_valid_value is not None:
        # Se il nuovo valore è più di 8 volte maggiore o minore
        # dell'ultima lettura valida, è quasi certamente un artefatto di
        # calcolo (non un cambiamento reale di attività in soli 10 minuti)
        # — lo scartiamo invece di pubblicarlo.
        ratio = value / last_valid_value if last_valid_value > 0 else float("inf")
        if ratio > 8 or ratio < 1 / 8:
            print(
                f"Valore {value} nm/s troppo distante dall'ultima lettura valida "
                f"({last_valid_value} nm/s): scarto come probabile artefatto."
            )
            value = None

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
        print("Nessun valore affidabile in questo ciclo: non aggiungo un punto.")

    thresholds = fixed_thresholds()
    generate_chart(history)

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
