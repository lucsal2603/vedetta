# Vedetta

Strumento di supporto per chi è di servizio davanti a un client di videosorveglianza (AXIS Camera Station).
Guarda lo schermo insieme a te e ti avvisa quando una persona prende qualcosa dallo scaffale e lo porta
al corpo, in tasca o in una borsa. Non si collega alle telecamere né al server, non riconosce i volti,
non manda nulla fuori dal PC. Salva solo una clip breve di ogni gesto segnalato.

**Non dice se la persona ha pagato.** Segnala il gesto: la decisione resta all'operatore.

## Come funziona

1. Cattura la porzione di schermo dove il client mostra la telecamera (o legge un file video di prova).
2. Un modello di posa (YOLO11 pose) trova le persone e la posizione di spalle, gomiti, polsi, fianchi.
3. Per ogni persona segue le mani: polso dentro una **zona scaffale** (disegnata una volta), lontano dal corpo,
   e poi, entro pochi secondi, polso al busto, ai fianchi o di lato con il gomito piegato.
4. Quando succede: suono, riquadro rosso, clip di 12 secondi in `clips/`, riga in `events.csv`.
5. Con i tasti `1` e `0` segni l'ultimo evento come vero o falso: serve per regolare le soglie.

## Uso sul Mac (sviluppo e prove)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python run.py                              # config.yaml: video di prova
.venv/bin/python run.py zone --source mele           # disegna le zone scaffale
.venv/bin/python -m unittest tests.test_gesture      # test del gesto
```

Test senza finestra, con video annotato in uscita:

```bash
.venv/bin/python run.py --config config.test.yaml --headless --out /tmp/prova.mp4
```

## Uso sul PC di lavoro (Windows)

Serve l'autorizzazione del datore di lavoro. Poi:

1. Scarica `Vedetta-windows.zip` dalla pagina **Releases** (o dagli artifact di Actions) e scompattalo in una cartella, per esempio `C:\Vedetta`.
2. Nel client crea una vista fissa con 1-4 riquadri grandi (le persone devono essere almeno 80-100 pixel di altezza).
3. `Riquadri.bat`: scrivi il nome del negozio (es. `via-milano`), porta davanti il client, trascina un rettangolo attorno a ogni riquadro, premi `s` e dai un nome a ciascuno. Il profilo `negozi\via-milano.yaml` viene scritto da solo.
4. `Zone.bat`: per ogni riquadro disegna i poligoni degli scaffali da sorvegliare (clic per i punti, INVIO chiude, `s` salva).
5. `Avvia Vedetta.bat`: scegli il negozio. Finestra con i riquadri, stato delle persone e allarmi.

Un profilo per ogni negozio: `negozi\<nome>.yaml` contiene i riquadri, le zone stanno in `zones\<nome>\`.
Nel profilo puoi anche cambiare `imgsz` e `fps_target` solo per quel negozio.

### Tasti nella finestra

| tasto | azione |
|---|---|
| `q` | esci |
| `p` | pausa |
| `s` | modalità silenziosa (registra ma non suona) |
| `1` | ultimo evento = vero |
| `0` | ultimo evento = falso |

Le zone si possono ridisegnare mentre il programma gira: al salvataggio vengono ricaricate.

## Impostazioni principali (`config.yaml`)

| chiave | cosa fa |
|---|---|
| `imgsz` | risoluzione di analisi. 640 veloce, 960-1280 per persone lontane in fondo alla corsia |
| `fps_target` | fotogrammi analizzati al secondo per riquadro (4-8) |
| `gesture.reach_min_s` | tempo minimo della mano nello scaffale |
| `gesture.conceal_window_s` | secondi dopo lo scaffale in cui cercare l'occultamento |
| `gesture.conceal_min_s` | tempo minimo della mano al corpo |
| `gesture.min_score` | sotto questo punteggio l'evento si registra ma non suona |
| `alert.silent_mode` | `true` la prima settimana: registra soltanto |
| `clips.keep_hours` | dopo quante ore le clip si cancellano da sole |

## Prima settimana

Tieni `silent_mode: true`. A fine turno apri `clips/` ed `events.csv`, guarda le clip e segna l'esito.
Le clip false dicono quale soglia alzare: se scattano quando la gente si sistema la giacca,
alza `conceal_min_s`; se scattano su persone che passano davanti allo scaffale, restringi le zone
o alza `reach_min_s`.

## Limiti noti

- Vede in due dimensioni: una persona in primo piano con lo scaffale alle spalle può sovrapporsi alla zona.
  La regola "polso lontano dal corpo" toglie la maggior parte di questi casi, non tutti.
- Persone piccole (in fondo alla corsia) hanno polsi poco affidabili: meglio un riquadro solo sulla metà vicina.
- Se cambi vista nel client mentre gira, i riquadri non corrispondono più: metti in pausa con `p`.
- Su un PC senza scheda video, 2 riquadri a 960 sono il massimo ragionevole.

## Compilazione per Windows

Il Mac non può creare l'eseguibile Windows. Lo fa GitHub Actions a ogni push su `main`
(`.github/workflows/build-windows.yml`): PyInstaller con torch solo CPU, cartella `Vedetta-windows.zip`
scaricabile dagli artifact; con un tag `v*` diventa anche una Release.

## Privacy

Il trattamento resta del negozio: informativa aggiornata, valutazione d'impatto e, se le telecamere riprendono
i dipendenti, quanto previsto dallo Statuto dei Lavoratori. Nessun riconoscimento biometrico.
