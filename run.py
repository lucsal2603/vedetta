#!/usr/bin/env python3
"""Avvio di Vedetta.

    python run.py                          # analisi (finestra)
    python run.py --silent                 # analisi in modalità silenziosa
    python run.py zone --source corsia-3   # editor zone scaffale
    python run.py riquadri --write         # selettore riquadri sullo schermo
"""
import sys

if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "zone":
        from vedetta.tools.zone_editor import main
        sys.exit(main(args[1:]))
    if args and args[0] == "riquadri":
        from vedetta.tools.region_picker import main
        sys.exit(main(args[1:]))
    from vedetta.app import main
    sys.exit(main(args))
