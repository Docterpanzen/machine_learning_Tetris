Tests — Übersicht

Dieser Ordner enthält Beispieltests für das Projekt. Ziel ist nicht, das komplette Training in CI laufen zu lassen, sondern:

- Unit-Tests für deterministische Funktionen (z.B. Reward-Berechnung)
- Env-API-Checks (Verwendung von `check_env`)
- Integrationstest-Beispiel mit TCP-Stub (simuliert Java-Server)

Dateien

- `test_reward.py` — Unit-Tests für die Reward-Logik (beispielhafte, isolierte Funktion `compute_reward`).
- `test_env_api.py` — Integrationstest, der einen einfachen TCP-Stub startet. Der Test überspringt sich automatisch, wenn `TetrisEnv` nicht importierbar ist.

Wie man die Tests ausführt

1. Stelle sicher, dass die Test-Dependencies installiert sind (pytest):

```bash
pdm add -d pytest
pdm install
```

oder systemweit:

```bash
python -m pip install pytest
```

2. Tests ausführen mit `pdm` (empfohlen):

```bash
pdm run pytest -q
```

oder direkt (wenn du `pdm`-venv aktiviert hast):

```bash
pytest -q
```

Hinweise

- Der Integrationstest (`test_tetrisenv_with_stub`) erwartet, dass die `TetrisEnv`-Klasse in ein importierbares Modul (`tetris_env.py`) verschoben wird. Wenn du die Klasse noch im Notebook hast, wird dieser Test automatisch übersprungen.
- Extrahiere die Reward-Berechnung in eine Funktion (z. B. `compute_reward`) innerhalb deines Projektmoduls, damit `test_reward.py` direkt die Produktionsfunktion importieren kann, anstatt die Testimplementierung zu verwenden.
- Halte Smoke-Tests kurz (z.B. <= 500 Steps) für CI.

Wenn du möchtest, kann ich:

- `TetrisEnv` in ein Modul `tetris_env.py` extrahieren und die Tests so zum Laufen bringen,
- eine GitHub Actions CI-Workflow-Datei anlegen, die die Tests kurz laufen lässt.