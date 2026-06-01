# Tetris Reinforcement Learning

## Überblick

Dieses Projekt trainiert einen Reinforcement-Learning-Agenten, der Tetris über eine eigene Gymnasium-Umgebung spielt. Die Umgebung verbindet sich mit einem Java-Tetris-Server und liefert pro Schritt ein Bild des Spielfelds, Zustandswerte und eine Belohnung zurück.

Die wichtigsten Bausteine sind:

- `TetrisEnv`: benutzerdefinierte Gymnasium-Umgebung
- `A2C`: der verwendete Lernalgorithmus aus Stable Baselines3
- `CnnPolicy`: Policy-Netzwerk für Bildverarbeitung
- Java-Tetris-Server: stellt das Spiel und die Zustandsdaten bereit

## Voraussetzungen

Bevor das Notebook sinnvoll läuft, müssen folgende Dinge vorhanden sein:

- Python-Umgebung über `pdm`
- Installierte Abhängigkeiten, insbesondere `gymnasium`, `stable-baselines3`, `opencv-python`, `imageio`, `numpy`
- Java 17 oder kompatible Java-Laufzeitumgebung
- Die Datei `TetrisTCPserver_v0.6.jar` im Projektordner

Wichtig ist außerdem die Reihenfolge beim Ausführen:

1. Bibliotheken importieren
2. Stable Baselines3 importieren
3. Java-Server starten
4. `TetrisEnv` definieren
5. Umgebung mit `check_env` testen
6. Parallele Umgebungen erzeugen
7. Modell trainieren
8. Modell testen und Ergebnisse speichern

## Teil 1: Testen der Umgebung

Der Testteil ist wichtig, weil er prüft, ob die Umgebung formal zu Gymnasium und Stable Baselines3 passt.

### Was der Test macht

Die Zelle mit `check_env(env)` überprüft unter anderem:

- ob die Klasse von `gymnasium.Env` erbt
- ob `action_space` und `observation_space` korrekt definiert sind
- ob `reset()` und `step()` die erwarteten Rückgabewerte liefern
- ob Beobachtungen zum deklarierten Space passen
- ob die Action- und Observation-Daten zu Stable Baselines3 kompatibel sind

### Was dabei in diesem Projekt schiefgehen kann

Im Projekt gibt es drei typische Ursachen für Fehler:

- **Falsche SB3-Version im Kernel**: Wenn noch eine alte Version geladen ist, kann `check_env` Fehler werfen, obwohl der Code korrekt aussieht.
- **Java-Server läuft nicht**: Dann scheitert schon `TetrisEnv()` beim Verbindungsaufbau.
- **Notebook-Kernel ist nicht neu gestartet**: Nach einem Paketwechsel bleibt sonst die alte importierte Version aktiv.

### Erwarteter Ablauf beim Testen

Wenn alles korrekt eingerichtet ist, sollte der Ablauf so aussehen:

- Server-Zelle starten
- `TetrisEnv()` erzeugen
- `check_env(env)` ausführen
- keine AssertionErrors oder ConnectionErrors
- Umgebung mit `env.close()` sauber schließen

## Teil 2: Das eigentliche Spiel / Training

Sobald die Umgebung validiert ist, wird sie für das Training verwendet.

### Wie die Umgebung arbeitet

Die Klasse `TetrisEnv` kommuniziert über TCP mit dem Java-Server. Pro Schritt passiert Folgendes:

1. Der Agent wählt eine Aktion aus
2. Die Aktion wird als Textkommando an den Server gesendet
3. Der Server berechnet die neue Spielsituation
4. Der Server sendet zurück:
   - ob das Spiel vorbei ist
   - wie viele Reihen entfernt wurden
   - die aktuelle Höhe
   - die Anzahl der Löcher
   - ein PNG-Bild des Spielfelds
5. Die Umgebung berechnet daraus die Belohnung
6. Das Ergebnis wird als `(observation, reward, terminated, truncated, info)` zurückgegeben

### Aktionen

Die Aktionenspace ist diskret und umfasst fünf Möglichkeiten:

- `0`: links bewegen
- `1`: rechts bewegen
- `2`: gegen den Uhrzeigersinn drehen
- `3`: im Uhrzeigersinn drehen
- `4`: Block fallen lassen

### Beobachtung

Die Beobachtung ist ein Bild des Spielfelds mit der Form:

- Höhe: `200`
- Breite: `100`
- Kanäle: `3`

Damit kann eine CNN-Policy direkt mit visuellen Informationen arbeiten.

### Training mit mehreren Umgebungen

Das Notebook erzeugt `16` parallele Umgebungen über `make_vec_env(TetrisEnv, n_envs=16)`.

Das hat zwei Effekte:

- mehr Erfahrung pro Zeiteinheit
- stabileres Lernen durch parallele Episoden

## Teil 3: Reward-Function im Detail

Die Belohnung ist der Kern des Projekts. Sie lenkt den Agenten in Richtung guter Tetris-Strategien.

### Grundidee

Die Reward-Funktion kombiniert mehrere Teilziele:

- Blöcke sinnvoll fallen lassen
- Reihen löschen
- Löcher reduzieren
- die Höhe des Spielfelds niedrig halten

### Exakte Logik

In der `step()`-Methode wird die Belohnung so aufgebaut:

```text
reward = 0

wenn action == 4:
    reward += 5

wenn height > vorherige Höhe:
    reward -= (height - vorherige Höhe) * 5

wenn holes < vorherige Lochanzahl:
    reward += (vorherige Lochanzahl - holes) * 10

wenn lines > vorherige Anzahl gelöschter Reihen:
    reward += (lines - vorherige Anzahl gelöschter Reihen) * 1000
```

### Bedeutung der einzelnen Teile

#### 1. Bonus für `drop`

Wenn der Agent `action == 4` ausführt, bekommt er `+5`.

Das belohnt das aktive Platzieren von Blöcken und fördert, dass der Agent nicht nur passiv herumbewegt.

#### 2. Strafe für höhere Türme

Wenn die neue Höhe größer ist als vorher, gibt es eine Strafe von `5` pro Höhenzuwachs.

Formel:

```text
-(height - alte_height) * 5
```

Das soll verhindern, dass sich das Spielfeld zu schnell nach oben füllt.

#### 3. Bonus für weniger Löcher

Wenn die Anzahl der Löcher sinkt, gibt es `+10` pro reduziertem Loch.

Formel:

```text
(alte_holes - holes) * 10
```

Das motiviert den Agenten, saubere Strukturen zu bauen und unnötige Hohlräume zu vermeiden.

#### 4. Sehr großer Bonus für gelöschte Reihen

Wenn mehr Reihen gelöscht wurden als im vorherigen Zustand, gibt es pro gelöschter Reihe `+1000`.

Formel:

```text
(lines - alte_lines_removed) * 1000
```

Das ist der stärkste Teil der Reward-Funktion, weil das eigentliche Ziel von Tetris das Entfernen von Reihen ist.

### Warum diese Gewichtung sinnvoll ist

Die Gewichtung zeigt klar die Priorität:

- Reihen löschen ist am wichtigsten
- Löcher vermeiden ist zweitrangig, aber sehr relevant
- die Höhe niedrig halten ist wichtig für langfristiges Überleben
- `drop` wird leicht belohnt, damit der Agent Aktionen nicht meidet

### Mögliche Nebenwirkungen

Diese Reward-Funktion kann dazu führen, dass der Agent stark auf Reihenlöschung optimiert und andere sinnvolle Langzeitstrategien erst später lernt. Außerdem ist die Reihenbelohnung deutlich größer als die anderen Teile, was das Lernen dominieren kann.

## Teil 4: Testen nach dem Training

Nach dem Training wird das Modell über 1000 Schritte getestet.

Dabei speichert das Notebook:

- das erste beobachtete Spiel
- das beste Spiel nach kumulativer Belohnung
- Screenshots aller Frames in `./replay`
- GIFs für beide Spiele
- eine CSV-Datei mit den Ergebnissen
- das trainierte Modell als ZIP-Datei

### Was beim Test verglichen wird

Für das erste und das beste Spiel werden unter anderem verglichen:

- entfernte Reihen
- Spieldauer in Schritten
- Gesamtbelohnung

Damit sieht man, ob der Agent nach dem Training besser geworden ist.

## Teil 5: Ausgabe und Artefakte

Am Ende erzeugt das Notebook diese Dateien:

- `best_game.gif`
- `first_game.gif`
- `tetris_results.csv`
- `tetris_a2c_trained_16env.zip`

## Empfohlene Ausführungsreihenfolge

1. Kernel starten
2. Imports ausführen
3. Java-Server starten
4. `TetrisEnv` definieren
5. `check_env(env)` ausführen
6. Parallele Umgebungen erzeugen
7. Modell trainieren
8. Modell testen
9. GIFs und CSV erzeugen

## Kurzfazit

Das Projekt zeigt eine komplette RL-Pipeline für Tetris:

- Umgebung validieren
- Spielzustand aus dem Server lesen
- Reward berechnen
- A2C-Modell trainieren
- Ergebnisse auswerten und visualisieren

Der wichtigste technische Punkt ist, dass das Notebook mit der richtigen SB3-Version im aktiven Kernel laufen muss und der Java-Server vor dem Env-Test gestartet sein muss.
