# Setup und Troubleshooting

Diese Anleitung bezieht sich auf die aktuelle Web-App mit FastAPI, Streamlit, `TetrisEnv` und Java-Tetris-Server. Die fachliche Gesamtdokumentation steht in [Tetris_Reinforcement_learning.md](Tetris_Reinforcement_learning.md).

## 1. Voraussetzungen prüfen

```bash
java -version
pdm --version
pdm run python --version
```

Das Projekt erwartet Python 3.12 und eine Java-Laufzeit, die `TetrisTCPserver_v0.6.jar` ausführen kann.

Auf Ubuntu/Debian kann Java beispielsweise so installiert werden:

```bash
sudo apt update
sudo apt install -y openjdk-17-jre-headless
```

## 2. Python-Abhängigkeiten installieren

Im Projektroot:

```bash
pdm install
```

`pdm.lock` hält die aufgelösten Versionen fest. Befehle sollten über `pdm run ...` ausgeführt werden, damit garantiert die Projektumgebung verwendet wird.

## 3. Empfohlener Start

Terminal 1:

```bash
pdm run backend
```

Terminal 2:

```bash
pdm run app
```

Prüfen:

```bash
curl http://127.0.0.1:8000/runs
curl http://127.0.0.1:8501/_stcore/health
```

Das Backend startet die Java-JAR automatisch. Ein manueller Start ist nur nötig, wenn ohne Backend gearbeitet wird:

```bash
java -jar TetrisTCPserver_v0.6.jar
```

## 4. `ConnectionRefusedError` oder „Tetris TCP Server nicht erreichbar“

Ursache: Auf `127.0.0.1:10612` läuft kein Tetris-Server.

```bash
ss -ltnp | grep 10612
tail -n 100 streamlit_logs/tetris_server.log
ls -l TetrisTCPserver_v0.6.jar
```

Mögliche Lösungen:

- Backend neu starten, damit es die JAR startet.
- Java-Installation mit `java -version` prüfen.
- Sicherstellen, dass die JAR im Projektroot liegt.
- Einen bereits hängenden Java-Prozess kontrolliert beenden und danach das Backend neu starten.

## 5. Backend ist nicht erreichbar

```bash
curl -v http://127.0.0.1:8000/runs
pdm run backend
```

Häufige Ursachen:

- Port `8000` ist bereits belegt.
- Uvicorn wurde aus einem anderen Arbeitsverzeichnis gestartet.
- Entwicklungsabhängigkeiten wurden nicht installiert.
- Beim Import tritt ein Python-Fehler auf; dieser steht im Backend-Terminal.

Das Frontend kann vorhandene Summarys lokal anzeigen, aber Prozessverwaltung und automatischer Java-Start fehlen ohne Backend.

## 6. Streamlit startet nicht oder zeigt das alte Theme

```bash
pdm run app
```

Nach Änderungen an `.streamlit/config.toml` Streamlit vollständig beenden und neu starten. Ein Browser-Reload allein übernimmt Theme-Konfigurationen nicht immer.

Wenn Port `8501` belegt ist:

```bash
pdm run streamlit run streamlit_app/app.py --server.port 8502
```

## 7. Run bleibt auf `running`

Der Status wird aus PID, SQLite-Eintrag und vorhandener `summary.json` abgeleitet.

```bash
cat streamlit_logs/current_run.json
tail -n 200 streamlit_logs/<runname>.log
ls -l training_runs/<runname>/summary.json
```

- Lebt der Prozess noch, läuft das Training möglicherweise weiter.
- Ist der Prozess beendet und eine Summary vorhanden, setzt ein erneuter API-Abruf den Status auf `completed`.
- Ohne Summary wird ein beendeter Prozess als `stopped` behandelt.

## 8. Training erzeugt kein Modell oder keine Summary

Zuerst das Runlog prüfen:

```bash
tail -n 250 streamlit_logs/<runname>.log
```

Typische Ursachen:

- TCP-Verbindung ist während des Trainings abgebrochen.
- Zu viele parallele Environments überlasten Server oder Rechner.
- Zu wenig Arbeitsspeicher für Bilddaten und CNN.
- Quellmodell eines Fortsetzungs-Runs fehlt oder passt nicht zum Algorithmus.
- Der Prozess wurde vor `model.save()` beendet.

Mit einer kleineren Konfiguration gegenprüfen:

```bash
pdm run python streamlit_app/train.py \
  --name smoke_test \
  --timesteps 1000 \
  --n_envs 1 \
  --algorithm A2C
```

## 9. Fortsetzen eines Modells schlägt fehl

Prüfen:

```bash
ls -lh models/<quellname>.zip
cat training_runs/<quellname>/summary.json
```

Der Algorithmus muss zur gespeicherten Modellklasse passen. Die Web-App übernimmt A2C oder PPO automatisch aus der Quelle. Bei direktem CLI-Aufruf muss `--algorithm` passend gesetzt werden.

Einen neuen Zielnamen verwenden, damit Quellmodell und Historie nicht überschrieben werden.

## 10. Gymnasium- oder Observation-Fehler

Die erwarteten Signaturen sind:

```python
reset() -> observation, info
step(action) -> observation, reward, terminated, truncated, info
```

Die Observation muss `shape == (200, 100, 3)` und `dtype == uint8` haben. Wenn OpenCV `None` liefert, ist das empfangene PNG ungültig oder unvollständig.

Umgebung und Versionen prüfen:

```bash
pdm run python -c "import gymnasium, stable_baselines3; print(gymnasium.__version__, stable_baselines3.__version__)"
pdm run pytest -q
```

## 11. Notebook verwendet falsche Pakete

Die Web-App benötigt keinen Notebook-Kernel. Für die experimentellen Notebooks kann der Projektinterpreter registriert werden:

```bash
pdm run python -m ipykernel install \
  --user \
  --name machine_learning \
  --display-name "machine_learning-3.12"
```

Danach diesen Kernel auswählen und nach Paketänderungen neu starten.

## 12. TensorBoard zeigt keine Daten

```bash
pdm run tensorboard --logdir tb_logs
find tb_logs -name 'events.out.tfevents.*' | head
```

Ein Eventfile entsteht erst, wenn Stable Baselines3 tatsächlich mit dem Lernen begonnen hat. Der Standardpfad eines direkten Trainings kann mit `--logdir` geändert werden.

## 13. Tests

```bash
pdm run pytest -q
```

Der TCP-Integrationstest verwendet Port `10613`, nicht den echten Port `10612`. Ist `10613` bereits belegt, kann der Test fehlschlagen. Die Java-JAR ist für diesen Test nicht erforderlich.

## 14. Diagnose-Checkliste

```bash
# Prozesse und Ports
ss -ltnp | grep -E '8000|8501|10612'

# API
curl http://127.0.0.1:8000/runs

# Versionen
pdm list --freeze

# Logs
tail -n 100 streamlit_logs/tetris_server.log
tail -n 100 streamlit_logs/<runname>.log

# Tests
pdm run pytest -q
```

Beim Debuggen zuerst von unten nach oben vorgehen: Java-Server, `TetrisEnv`, Trainingsprozess, FastAPI und zuletzt Streamlit. So lässt sich die fehlerhafte Schicht schneller eingrenzen.
