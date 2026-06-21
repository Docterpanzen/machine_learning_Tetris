# Blocklab – Tetris Reinforcement Learning

Dieses Projekt trainiert visuelle A2C- und PPO-Agenten für Tetris. Eine eigene Gymnasium-Umgebung verbindet Stable Baselines3 über TCP mit einem Java-Tetris-Server. FastAPI verwaltet Trainingsprozesse und Run-Metadaten; die Streamlit-Web-App bietet Training, Live-Monitoring, Historie, Modellverwaltung und einen Playground.

Die vollständige Erklärung von Architektur, Reinforcement Learning, Reward-Funktion, Algorithmen, API und Umsetzung steht in [docs/Tetris_Reinforcement_learning.md](docs/Tetris_Reinforcement_learning.md).

## Architektur in Kürze

```text
Streamlit -> FastAPI -> train.py -> TetrisEnv -> Java-Tetris-Server
    |           |           |
    |         SQLite     Modelle, GIFs, Summarys und TensorBoard
    └──────── lokale Fallbacks für vorhandene Artefakte
```

Wichtige Dateien:

- `tetris_env.py` – Gymnasium-Environment, TCP-Protokoll und Reward
- `streamlit_app/app.py` – Blocklab-Frontend
- `streamlit_app/backend.py` – FastAPI, SQLite und Prozessverwaltung
- `streamlit_app/train.py` – A2C-/PPO-Training
- `TetrisTCPserver_v0.6.jar` – Tetris-Spielserver
- `docs/Tetris_Reinforcement_learning.md` – zentrale Projektdokumentation
- `docs/Troubleshooting.md` – Einrichtung und Fehlerbehebung

## Voraussetzungen

- Python 3.12
- PDM
- Java-Laufzeit
- `TetrisTCPserver_v0.6.jar` im Projektroot

## Installation

```bash
pdm install
```

## Web-App starten

In zwei Terminals:

```bash
# Terminal 1: API, Runverwaltung und automatischer Java-Start
pdm run backend

# Terminal 2: Weboberfläche
pdm run app
```

Danach sind erreichbar:

- Web-App: `http://127.0.0.1:8501`
- Swagger/OpenAPI: `http://127.0.0.1:8000/docs`
- Tetris TCP-Server: `127.0.0.1:10612`

## Direktes Training

Wenn die JAR bereits läuft:

```bash
pdm run python streamlit_app/train.py \
  --name experiment_01 \
  --timesteps 100000 \
  --n_envs 8 \
  --algorithm PPO
```

## Tests

```bash
pdm run pytest -q
```

## Ergebnisse

- `models/` – gespeicherte Stable-Baselines3-Modelle
- `training_runs/` – JSON-Summary pro Run
- `gifs/` – Vorher-/Nachher- und Playground-GIFs
- `streamlit_logs/` – Trainings- und Java-Logs
- `tb_logs/` – TensorBoard-Events

```bash
pdm run tensorboard --logdir tb_logs
```
