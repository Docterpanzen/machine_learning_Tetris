# Blocklab-Frontend

`app.py` ist die Streamlit-Oberfläche des Tetris-RL-Projekts. Sie verändert keine Trainingsdaten selbst, sondern koordiniert Eingaben, API-Aufrufe und die Darstellung vorhandener Artefakte.

## Start

Das Backend sollte zuerst laufen:

```bash
pdm run backend
pdm run app
```

Die App ist standardmäßig unter `http://127.0.0.1:8501` erreichbar.

## Bereiche

- **Training:** A2C/PPO starten, Live-Log sehen und Modelle fortsetzen
- **Playground:** Modelle deterministisch ausführen, GIFs und Statistiken speichern
- **Modelle:** Metadaten anzeigen und Artefakte kontrolliert löschen
- **Historie:** abgeschlossene Runs und Vorher-/Nachher-GIFs vergleichen

## Datenzugriff

Bevorzugt ruft das Frontend FastAPI unter `http://127.0.0.1:8000` auf. Ist die API nicht erreichbar, liest es vorhandene `summary.json`-Dateien, Logs und Modelle direkt. Beim Trainingsstart kann es ebenfalls auf einen lokalen Subprozess zurückfallen; der Tetris-Server muss in jedem Fall auf Port `10612` erreichbar sein.

Das visuelle Theme steht in `.streamlit/config.toml`; ergänzende Komponentenstile liegen am Anfang von `app.py`.

Die vollständige Architektur ist in [../docs/Tetris_Reinforcement_learning.md](../docs/Tetris_Reinforcement_learning.md) dokumentiert.
