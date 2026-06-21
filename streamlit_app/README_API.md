# FastAPI-Backend

`backend.py` verwaltet Training-Subprozesse, Run-Metadaten und den Lebenszyklus des Java-Tetris-Servers.

## Start

```bash
pdm run backend
```

- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`
- SQLite: `streamlit_app.db`
- Java-Log: `streamlit_logs/tetris_server.log`

Beim Start prüft das Backend `127.0.0.1:10612` und startet `TetrisTCPserver_v0.6.jar`, wenn dort kein Server erreichbar ist.

## Endpunkte

| Methode | Pfad | Funktion |
|---|---|---|
| `POST` | `/runs/start` | A2C-/PPO-Training starten |
| `POST` | `/runs/stop/{name}` | Runprozess beenden |
| `GET` | `/runs` | Runs listen, optional nach Status filtern |
| `GET` | `/runs/{name}` | Run und Summary abrufen |
| `GET` | `/runs/{name}/log` | letzten Logabschnitt abrufen |
| WebSocket | `/ws/runs/{name}` | Status, Fortschritt und Log streamen |

Beispiel:

```bash
curl -X POST http://127.0.0.1:8000/runs/start \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "experiment_01",
    "timesteps": 100000,
    "n_envs": 8,
    "resume_from": null,
    "algorithm": "PPO"
  }'
```

Der Trainingsprozess schreibt nach `streamlit_logs/<name>.log`. Nach erfolgreichem Abschluss liest das Backend `training_runs/<name>/summary.json` und ergänzt damit API-Antworten.

Details zu Feldern, Fortschrittsberechnung und Systemarchitektur stehen in [../docs/Tetris_Reinforcement_learning.md](../docs/Tetris_Reinforcement_learning.md).
