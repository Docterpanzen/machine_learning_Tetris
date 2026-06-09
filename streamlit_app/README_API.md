FastAPI backend for Tetris RL Streamlit UI

Run the backend:

```bash
# from project root
pdm run backend
```

The backend starts `TetrisTCPserver_v0.6.jar` automatically on port `10612`.
Server output is written to `streamlit_logs/tetris_server.log`.

API endpoints:
- POST /runs/start  {name, timesteps, n_envs} -> starts a run and returns pid/log
- POST /runs/stop/{name} -> stops a run
- GET /runs -> returns all runs
- GET /runs/{name}/log -> returns tail of log

Notes:
- The backend stores run metadata in `streamlit_app.db` (SQLite) in the project root.
- The backend spawns `streamlit_app/train.py` as a subprocess and redirects stdout/stderr to `streamlit_logs/<name>.log`.
