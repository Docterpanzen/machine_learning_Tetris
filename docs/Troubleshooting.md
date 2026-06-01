# Setup-Anleitung — Tetris Reinforcement Learning

Diese Anleitung hilft dir, die Entwicklungsumgebung vollständig einzurichten: Java installieren, Python-Umgebung einrichten (PDM), Abhängigkeiten installieren und typische Fehler beheben.

## 1) Java 17 installieren (JRE)

Auf Ubuntu/Debian-basierten Systemen:

```bash
sudo apt update
sudo apt install -y openjdk-17-jre-headless
java -version
```

Wenn `openjdk-17` nicht gefunden wird, verwende die paket-spezifische Version `openjdk-17-jre-headless` (wie oben). Falls dein System eine andere Distribution ist, nutze den Paketmanager deiner Distribution oder lade OpenJDK von adoptopenjdk/Temurin.

## 2) Python-Umgebung mit PDM

Projekt verwendet `pdm` zur Paketverwaltung. Falls du `pdm` nicht installiert hast:

```bash
python3 -m pip install --user pdm
# oder systemweit
# pip install pdm
```

Initialisiere / aktiviere die venv (falls vorhanden):

```bash
# Optional: nutze die im Projekt erstellte venv
source .venv/bin/activate
# Oder pdm-venv aktivieren
pdm venv activate
```

## 3) Abhängigkeiten installieren

Wenn du die `pdm.lock` bereits hast (empfohlen), installiere genau die gelockten Versionen:

```bash
pdm install
```

Wenn du zusätzliche Pakete hinzufügen willst oder eine frische Installation ohne Lock:

```bash
pdm add "stable-baselines3[extra] >= 2.0.0a5"
pdm add ipykernel gymnasium opencv-python imageio numpy
# oder alle Anforderungen auf einmal (wenn du pyproject.toml angepasst hast)
pdm lock
pdm install
```

Falls du Jupyter-Notebook-Kernel registrieren willst:

```bash
pdm run python -m ipykernel install --user --name=machine_learning --display-name="machine_learning-3.12"
```

## 4) Java-Tetris-Server starten

Stelle sicher, dass `TetrisTCPserver_v0.6.jar` im Projektverzeichnis liegt. Zum Starten im Hintergrund (Notebook-Cell):

```python
import subprocess
server_process = subprocess.Popen(["java", "-jar", "TetrisTCPserver_v0.6.jar" ])
```

In Shell:

```bash
java -jar TetrisTCPserver_v0.6.jar &
```

Der Server sollte auf Port `10612` lauschen (siehe Notebook-Ausgabe).

## 5) Notebook ausführen (Empfohlene Reihenfolge)

1. Öffne `Tetris_Reinforcement_learning.ipynb`
2. Starte Kernel (verwende die `pdm`-venv oder `.venv`)
3. Führe die Import-Zelle aus
4. Führe die Zelle zum Starten des Java-Servers aus
5. Führe die Zelle mit der `TetrisEnv`-Definition aus
6. Führe `check_env(env)` aus
7. Erstelle `vec_env` und trainiere das Modell
8. Testen & GIF erstellen

Wichtig: Nach jeder Paket-Änderung `Kernel → Restart` im Notebook ausführen.

## 6) Häufige Fehler & Lösungen

- `python: No module named pip` beim Versuch, `ipykernel` zu installieren:
  - Lösung: Verwende `pdm install` statt `python -m pip`, oder aktiviere die venv mit `source .venv/bin/activate`.

- `AssertionError: Your environment must inherit from the gym.Env` bei `check_env`:
  - Ursache: Alte `stable-baselines3` oder Kernel lädt noch eine alte Version.
  - Lösung: `pdm add "stable-baselines3[extra] >= 2.0.0a5"`, `pdm install` → Kernel-Neustart, dann Zellen neu ausführen.

- `ConnectionRefusedError` beim Erzeugen von `TetrisEnv()`:
  - Ursache: Java-Server läuft nicht oder lauscht auf anderem Port.
  - Lösung: Starte `TetrisTCPserver_v0.6.jar` und prüfen, dass Port `10612` offen ist. In der Shell:

```bash
ss -lntp | grep 10612
# oder
netstat -lntp | grep 10612
```

- `ModuleNotFoundError` in Notebook (Module installiert, aber nicht gefunden):
  - Ursache: Notebook-Kernel verwendet eine andere Python-Umgebung als die `pdm`-venv.
  - Lösung: Stelle in VS Code / Jupyter sicher, dass der Kernel auf `.venv/bin/python` bzw. `pdm` venv eingestellt ist oder installiere den Kernel mit `pdm run python -m ipykernel install ...`.

- `stable-baselines3`-Versionen und Kompatibilität:
  - SB3 1.x ist nicht vollständig kompatibel mit `gymnasium`. Verwende die SB3 2.x alpha/beta für Gymnasium-Unterstützung.

## 7) Quick-check Befehle

```bash
# Prüfe Java
java -version

# Prüfe Python in venv
source .venv/bin/activate
python -c "import sys, site; print(sys.executable); print(site.getsitepackages())"

# Installiere alle Abhängigkeiten
pdm install

# Starte Notebook
pdm run jupyter lab
```

---

Wenn du willst, kann ich jetzt noch: 
- die README-Links überprüfen (automatisch öffnen/lesen),
- die Setup-Datei auf Englisch übersetzen, oder
- eine Troubleshooting-Seite mit Log-Beispielen anlegen.# Setup & Troubleshooting — Tetris Reinforcement Learning

Diese Anleitung führt dich Schritt für Schritt durch die Einrichtung der Entwicklungsumgebung, das Starten des Java-Tetris-Servers und die Installation der Python-Abhängigkeiten mit `pdm`. Außerdem sind häufige Fehler und schnelle Lösungswege aufgeführt.

## 1) Systemanforderungen

- Linux (Anleitung unten). Auf macOS/Windows weichen einige Befehle ab.
- Java 17 JRE (oder JDK)
- `pdm` (Python-Dependency-Manager)
- Git (optional)

## 2) Java 17 installieren (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y openjdk-17-jre-headless
java -version
```

macOS (Homebrew):

```bash
brew install openjdk@17
# ggf. PATH anpassen
```

Windows: lade das JRE/JDK von adoptium.net oder adoptopenjdk.net und installiere es.

Prüfe die Installation mit:

```bash
java -version
# Ausgabe sollte Java 17 zeigen
```

## 3) Projekt klonen / in das Projektverzeichnis wechseln

```bash
cd /path/to/project
# falls noch nicht geklont:
# git clone <repo>
```

## 4) PDM-Umgebung nutzen

Wenn `pdm` noch nicht installiert ist, installiere es (System-weit oder in einer venv):

```bash
python -m pip install --user pdm
```

Initiale Installation aller Abhängigkeiten (aus `pyproject.toml` / `pdm.lock`):

```bash
pdm install
```

Wenn du ein Paket hinzufügen willst (z. B. Stable Baselines3):

```bash
pdm add "stable-baselines3[extra] >= 2.0.0a5"
pdm add -d ipykernel
```

Hinweis: `pdm install` verwendet `pdm.lock` (falls vorhanden) und installiert exakt die gesperrten Versionen.

## 5) venv/Kernel aktivieren und `ipykernel` registrieren

Es gibt zwei Optionen:

- Arbeitsweise mit `pdm run` (empfohlen für Konsistenz), oder
- die `pdm`-venv als Kernel in Jupyter registrieren.

Aktiviere venv (wenn du die Shell-venv verwendest):

```bash
source .venv/bin/activate
```

Oder aktiviere pdm-venv (pdm venv aktivieren):

```bash
pdm venv activate  # falls pdm die venv verwaltet
```

`ipykernel` in Jupyter registrieren (damit der Kernel in VS Code / Notebook auswählbar ist):

```bash
pdm run python -m ipykernel install --user --name=machine_learning --display-name="machine_learning-3.12"
```

Danach wähle in VS Code den Kernel `machine_learning-3.12` aus und starte den Notebook-Kernel neu.

## 6) Java-Tetris-Server starten

Stelle sicher, dass `TetrisTCPserver_v0.6.jar` im Projektverzeichnis liegt.

```bash
# im Projektordner
java -jar TetrisTCPserver_v0.6.jar &
# prüfen, ob Port 10612 hört (Linux):
ss -ltnp | grep 10612
```

Die Notebook-Zelle zum Starten des Servers macht das automatisch, du kannst sie aber auch manuell laufen lassen.

## 7) Notebook ausführen — empfohlene Reihenfolge

1. Zellen mit Imports ausführen
2. Java-Server starten (oder vorher manuell starten)
3. `TetrisEnv`-Definition ausführen
4. `check_env(env)` ausführen (prüft Gym-API-Protokoll)
5. Parallele Umgebungen erzeugen (`make_vec_env`) und trainieren

Wichtig: Nach jeder Paketinstallation Kernel neu starten.

## 8) Häufige Fehler und schnelle Lösungen

### Problem A — `python: No module named pip` oder `ipykernel` konnte nicht installiert werden

Ursache: venv ist nicht vollständig initialisiert oder `pip`/`ensurepip` fehlt.

Lösung (mit `pdm`-Kontext):

```bash
# Versuch zuerst mit pdm:
pdm install
# Falls pip im venv fehlt:
python -m ensurepip --upgrade
python -m pip install --upgrade pip
# Dann ipykernel über pdm installieren bzw. registrieren:
pdm add -d ipykernel
pdm run python -m ipykernel install --user --name=machine_learning --display-name="machine_learning-3.12"
```

Wenn du `sudo` verwenden musst, vermeide die Installation in die System-Python-Umgebung — besser ist die Nutzung von `pdm`.

---

### Problem B — `AssertionError: Your environment must inherit from the gym.Env class`

Ursache: Kernel hatte eine ältere `stable-baselines3`-Version geladen (z. B. 1.x), die andere Checks erwartet.

Prüfen:

```python
import stable_baselines3
print(stable_baselines3.__version__)
import gymnasium as gym
print(gym.__file__)
```

Lösung:

- Stelle sicher, dass `stable-baselines3` >= 2.0 (oder die im Projekt benötigte Variante) installiert ist:

```bash
pdm add "stable-baselines3[extra] >= 2.0.0a5"
```

- Kernel neu starten (unbedingt) damit die neue SB3-Version importiert wird.

---

### Problem C — `ConnectionRefusedError` beim Erzeugen von `TetrisEnv()`

Ursache: Java-Server läuft nicht oder wurde auf anderem Port gestartet.

Lösung:

- Java-Server starten: `java -jar TetrisTCPserver_v0.6.jar` oder die Notebook-Zelle ausführen.
- Prüfe Logs/Terminal-Ausgabe des Servers.
- Prüfe Port mit `ss -ltnp | grep 10612`.

---

### Problem D — `check_env` findet Methoden/Return-Tuple nicht korrekt

Ursache: `step()` oder `reset()` liefern nicht die erwartete Signatur.

Erwartetes `step()`-Return:

```python
observation, reward, terminated, truncated, info
```

Erwartetes `reset()`-Return:

```python
observation, info
```

Lösung:

- Prüfe, dass alle diese Werte geliefert werden und `observation` in den Bereich `observation_space` passt.
- Testweise kann man `print(type(observation), observation.shape)` in `step()` ausgeben.

---

### Problem E — Notebook zeigt alte Versionen nach `pdm add`/`pdm install`

Ursache: Kernel wurde nicht neu gestartet oder VS Code verwendet anderen Interpreter.

Lösung:

1. Kernel neu starten in Jupyter/VS Code
2. In VS Code: Python-Interpreter (unten rechts) auf die `pdm`-venv setzen (`.venv/bin/python`)
3. Prüfen mit `import stable_baselines3; print(stable_baselines3.__version__)`

## 9) Quick-checkliste zum Debuggen

- Läuft Java? `java -version` / `ss -ltnp | grep 10612`
- Stimmt der Kernel? Kernel neu starten, Kernel auf `machine_learning-3.12` setzen
- SB3-Version prüfen: `pdm run python -c "import stable_baselines3; print(stable_baselines3.__version__)"`
- ipykernel registriert? `jupyter kernelspec list`

## 10) Weiteres

Wenn du willst, kann ich die `pyproject.toml` prüfen und ggf. eine präzisere Liste von Abhängigkeiten in `pyproject.toml` vorschlagen, oder die README um eine englische Variante erweitern.

---

Datei: `docs/SETUP.md`
