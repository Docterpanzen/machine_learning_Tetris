# Tetris Reinforcement Learning (Übersicht)

Kurz: Dieses Repository trainiert einen Reinforcement-Learning-Agenten (A2C) für Tetris. Die Umgebung `TetrisEnv` verbindet sich mit einem Java-basierten Tetris-Server (`TetrisTCPserver_v0.6.jar`) über TCP und liefert Spielfeldbilder sowie Spielzustands-Metadaten.

- Doku: [Documentation](docs/Tetris_Reinforcement_learning.md)
- Troubleshooting: [Troubleshooting.md](docs/Troubleshooting.md)
- Haupt-Notebook: [Tetris_Reinforcement_learning.ipynb](Tetris_Reinforcement_learning.ipynb)
- Java-Server: `TetrisTCPserver_v0.6.jar`

Projektstruktur (wichtigste Dateien):

- `Tetris_Reinforcement_learning.ipynb` — Notebook mit kompletter Pipeline (Import, Server-Start, Env-Definition, Training, Testen, GIF-Erzeugung)
- `Tetris_Reinforcement_learning_GPU.ipynb` — GPU-optimierte Variante
- `TetrisTCPserver_v0.6.jar` — Java-Tetris-Server (muss ausführbar sein)
- `docs/Tetris_Reinforcement_learning.md` — Detaillierte Projekt-Dokumentation (Testen, Spielablauf, Reward-Funktion, Artefakte)

- `tests/` — Beispieltests und Testanleitungen
   - `tests/test_reward.py` — Unit-Tests für die Reward-Logik
   - `tests/test_env_api.py` — Integrationstest mit TCP-Stub (überspringt sich, wenn `TetrisEnv` nicht importierbar ist)
   - `tests/TESTS.md` — Anleitung zum Ausführen der Tests

Kurzanleitung zum Starten

1. Umgebung aktivieren (PDM/venv):

```bash
source .venv/bin/activate
# oder wenn du pdm-workspace nutzt:
# pdm venv activate
```

2. Abhängigkeiten installieren (mit `pdm`):

```bash
pdm install
```

3. Java 17 (JRE) installieren, falls noch nicht vorhanden:

```bash
sudo apt update
sudo apt install -y openjdk-17-jre-headless
java -version
```

4. Notebook starten und in dieser Reihenfolge ausführen:
   - Zelle mit Imports
   - Zelle zum Starten des Java-Servers
   - Zelle mit `TetrisEnv`-Definition
   - Zelle mit `check_env(env)` (prüft Gym-Kompatibilität)
   - Zellen zum Erstellen von `vec_env` und Modelltraining

Wichtiger Hinweis

- Nach Paketänderungen (z. B. `stable-baselines3`) immer den Notebook-Kernel neu starten, damit die neue Version geladen wird.
- Der Java-Server muss laufen bevor `TetrisEnv()` konstruiert wird, sonst tritt `ConnectionRefusedError` auf.

Nächste Schritte

- Lies die ausführliche Doku in `docs/Tetris_Reinforcement_learning.md` für Details zur Reward-Funktion und zu Tests.
- Sag mir, ob ich die README auf Englisch übersetzen oder zusätzliche Links (z. B. zu Troubleshooting) ergänzen soll.
