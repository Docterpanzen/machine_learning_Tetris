# Tests

Die Tests sollen schnelle, deterministische Fehler erkennen, ohne ein vollständiges RL-Training oder die Java-JAR zu starten.

## Ausführen

```bash
pdm install
pdm run pytest -q
```

## Dateien

- `test_reward.py` prüft konkrete Beispiele der derzeitigen Reward-Gewichtung.
- `test_env_api.py` ist als TCP-Integrationstest auf Port `10613` angelegt und soll die echte `TetrisEnv`, `reset()` und `step()` prüfen.

Der Stub sendet dasselbe grundlegende Binärformat wie der Java-Server: Game-Over-Byte, Zeilen, Höhe, Löcher, Bildlänge und PNG.

Im aktuellen Projektstand ergibt `pdm run pytest -q` drei bestandene Reward-Tests und einen übersprungenen TCP-Test, weil `TetrisEnv` über den Pytest-Konsolenaufruf nicht aufgelöst wird. Bei einem erzwungenen Projektimport muss außerdem das eingebettete Test-PNG mit der aktuellen OpenCV-Version kompatibel sein. Der Integrationstest ist deshalb gegenwärtig Testgerüst, noch keine verlässliche Abdeckung.

## Abgrenzung

Die Suite prüft derzeit nicht:

- Qualität oder Konvergenz eines trainierten Modells,
- einen vollständigen Run über FastAPI,
- die Streamlit-Darstellung,
- die echte Java-JAR,
- A2C/PPO-Hyperparameter.

Die Reward-Berechnung ist in `test_reward.py` aktuell als kleine Referenzfunktion dupliziert. Für stärkeren Schutz sollte sie künftig aus `tetris_env.py` importiert werden, nachdem die Produktionslogik dort in eine eigenständige `compute_reward`-Funktion extrahiert wurde.

Für den TCP-Test sollten zusätzlich der Projektroot als Pytest-Pythonpfad konfiguriert und ein nachweislich gültiges PNG-Testfixture verwendet werden.
