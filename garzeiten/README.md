# Die wichtigsten Garzeiten – Rekonstruktion (Handbuch Dampfdruckkocher, S. 12–15)

| Datei | Inhalt |
|---|---|
| `garzeiten.csv` | Alle 106 Zeilen der vier Tabellenseiten (UTF-8, Komma-getrennt). Spalten: `seite`, `typ` (eintrag / hinweis / spaltenkopf / fussnote), `gruppe`, `label` (gedruckte Randbeschriftung, `\n` = Zeilenumbruch), `symbol` (○ / *), `gericht`, `garzeit_eingeweicht_min`, `garzeit_min`, `einsatz`, `wasser`, `anmerkung` |
| `garzeiten.pdf` | Die vier Seiten, aus der CSV gesetzt (A5, Liberation Serif) |
| `rectified/` | Rektifizierte Fotos: `pageNN_color.png` (entzerrt), `pageNN_clean.png` (zusätzlich Beleuchtung geglättet, kontrastverstärkt), `pageNN_rules.json` (erkannte Tabellenlinien) |
| `compare/sideNN.jpg` | Rektifiziertes Original (links) neben der PDF-Seite (rechts), auf gleiche Zeilenhöhe skaliert |
| `src/rectify.py` | Entzerrung: globale Drehung, dann werden alle gestrichelten Tabellenlinien als Kurven verfolgt und geradegezogen (Dewarp), Zuschnitt, Beleuchtungsausgleich |
| `src/build_pdf.py` | Erzeugt `garzeiten.pdf` aus `garzeiten.csv` |
| `src/compare.py` | Erzeugt die Vergleichsbilder |

Neu bauen: `python3 src/rectify.py && python3 src/build_pdf.py && pdftoppm -r 150 -png garzeiten.pdf compare/pdf && python3 src/compare.py`

## Unsichere Lesungen
Die Wassermengen-Brüche (⅛ l, ¼ l, ½ l) sind im Original stark abgerieben. Entschieden wurde nach der Form des Nenners (x-förmig = 8, offen = 4) und nach dem Kontext; alle nicht eindeutig lesbaren Zellen sind in der Spalte `anmerkung` markiert:
Ragout oder Gulasch (Fisch), Hähnchen ganz, Grünkohl/Rotkohl, Kartoffeln in der Schale, Kohlrouladen/Krautwickel, Rote Rüben/Bete, Schwarzwurzeln, Zwiebeln ganze sowie die erste Ziffer bei Rebhühner (3–6 Eßlöffel, analog Fasan).

Nicht reproduziert: der Bibliotheksstempel unten auf Seite 15 (die Seitenzahl 15 darunter ist im Original verdeckt und wurde ergänzt).
