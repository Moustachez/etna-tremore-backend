# EtnaTremoreBackend

Calcola il tremore vulcanico dell'Etna dai dati sismici grezzi e ufficiali
dell'INGV, e lo pubblica gratis come file JSON online, aggiornato ogni 10
minuti — usando solo strumenti gratuiti di GitHub (Actions + Pages), senza
bisogno di un server proprio.

## Come funziona (in breve)

1. Ogni 10 minuti, **GitHub Actions** esegue automaticamente uno script
   Python (`scripts/compute_tremor.py`)
2. Lo script scarica le forme d'onda sismiche grezze dalle stazioni INGV
   sull'Etna (rete IV: ECPN, ECBD, ECNE, EMFS — le stesse usate nei
   bollettini ufficiali), calcola il valore RMS in nm/s
3. Il risultato viene salvato in `docs/tremore.json` e pubblicato
   automaticamente da **GitHub Pages** come pagina web pubblica
4. L'app iOS legge quel file per mostrare il valore numerico del tremore

## 1. Crea un account GitHub (se non ce l'hai)

1. Vai su https://github.com e clicca "Sign up"
2. Segui la procedura (email, password, nome utente)
3. È gratuito, non serve carta di credito per quello che useremo

## 2. Crea un nuovo repository

1. Una volta loggato, clicca il "+" in alto a destra → "New repository"
2. Nome: `etna-tremore-backend` (o quello che preferisci)
3. Lascialo **Public** (necessario per GitHub Pages gratuito)
4. NON spuntare "Add a README" (lo abbiamo già)
5. Clicca "Create repository"

## 3. Carica i file di questo progetto

Nella pagina del repository appena creato, GitHub mostra un link tipo
"uploading an existing file" — usalo:

1. Clicca su "uploading an existing file" (o vai su Add file → Upload files)
2. Trascina dentro **tutta** la cartella `EtnaTremoreBackend` che hai
   scaricato (o i singoli file mantenendo la stessa struttura di cartelle:
   `.github/workflows/tremore.yml`, `docs/tremore.json`,
   `scripts/compute_tremor.py`, `scripts/requirements.txt`)
3. In basso, scrivi un messaggio tipo "Primo caricamento" e clicca
   "Commit changes"

> Nota: se il tuo browser non ti fa trascinare intere cartelle con
> sottocartelle, carica un file alla volta usando "Add file → Create new
> file" e scrivendo il percorso completo (es. `docs/tremore.json`) nel
> campo del nome — GitHub crea le cartelle automaticamente.

## 4. Attiva GitHub Pages

1. Nel repository, vai su **Settings** (in alto)
2. Nel menu a sinistra, clicca **Pages**
3. Sotto "Build and deployment" → "Source", scegli **Deploy from a branch**
4. Branch: `main`, cartella: **/docs** → clicca **Save**
5. Dopo un minuto o due, in cima alla stessa pagina apparirà l'indirizzo
   pubblico del tuo sito, tipo:
   `https://tuonome.github.io/etna-tremore-backend/`

Il file JSON sarà raggiungibile a:
`https://tuonome.github.io/etna-tremore-backend/tremore.json`

**Copia questo indirizzo**, ti servirà per collegare l'app.

## 5. Avvia manualmente il primo calcolo (non aspettare i 10 minuti)

1. Vai sulla tab **Actions** in alto nel repository
2. A sinistra clicca **Calcola tremore Etna**
3. A destra clicca **Run workflow** → **Run workflow** (di nuovo, per
   confermare)
4. Attendi 1-2 minuti, poi ricarica: dovresti vedere un pallino verde ✅
5. Apri l'indirizzo del file JSON (passo 4) nel browser: dovresti vedere i
   dati aggiornati, con `"latest"` che mostra il valore più recente

Da questo momento lo script gira da solo ogni 10 minuti, senza che tu debba
fare nulla — anche a PC spento, perché gira sui server di GitHub, non sul
tuo computer.

## Se il workflow fallisce (pallino rosso ❌)

1. Clicca sull'esecuzione fallita nella tab Actions per vedere il log
   dell'errore
2. Le cause più comuni: nessuna stazione con dati disponibili in quel
   momento (raro, lo script riprova da solo al ciclo successivo), oppure un
   problema temporaneo del servizio INGV
3. Se vedi un errore diverso, incollamelo pure e lo risolviamo insieme,
   come abbiamo fatto per l'app

## Nota sui limiti gratuiti di GitHub Actions

Il piano gratuito include 2.000 minuti al mese per i repository pubblici —
di fatto illimitato per questo utilizzo (uno script che gira ogni 10 minuti
e impiega pochi secondi consuma una piccola frazione di quel budget).

## Prossimo passo

Una volta che il file JSON è online e si aggiorna correttamente, dammi
l'indirizzo pubblico (quello del passo 4) e aggiorno l'app per leggere il
valore numerico reale del tremore, invece del grafico incorporato.
