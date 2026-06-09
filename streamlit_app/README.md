Streamlit UI for Tetris Reinforcement Learning

Run the Streamlit app to control training runs, see logs and view generated GIFs.

Usage:

1. Install Streamlit in your pdm environment:

```bash
pdm add -d streamlit
pdm install
```

2. Launch the app:

```bash
pdm run streamlit run streamlit_app/app.py
```

What it does:

- Start a training run (`train.py`) as a background subprocess
- Capture stdout/stderr into `streamlit_logs/<name>.log`
- Display the log tail and any generated GIFs from `gifs/`

Notes:

- The app calls `streamlit_app/train.py` which expects the project to provide `tetris_env.TetrisEnv` and Stable Baselines3.
- For production you may want to run training as a managed service and show logs via a logging backend.