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
| `aligned/pageNN_color.png`, `_clean.png` | Original pixelgenau auf die PDF-Seite (300 dpi) registriert |
| `diff/pageNN_diff.png` | Differenzbild: schwarz = Tinte in Original und PDF, rot = nur Original, blau = nur PDF (1 px Toleranz) |
| `diff/pageNN_side.jpg` | registriertes Original (links) neben dem Differenzbild (rechts) |
| `diff/schwierige_faelle.pdf` / `_1..4.png` | Schwierige Zellen: Original, Differenz und gerenderte Lesarten mit Korrelationswert; letzte Seite: weitere Zellen mit geringster Übereinstimmung |
| `src/align.py` | Registrierung: Tabellenlinien des Originals werden per dynamischer Programmierung den PDF-Linien zugeordnet (y), die x-Skala kommt aus zeilenweiser Profilkorrelation, der x-Versatz aus dem Namensblock; danach affine ECC-Feinkorrektur, falls sie die Überdeckung verbessert |
| `src/measure_layout.py` | misst aus der Registrierung die Spaltenversätze Original vs. PDF (fließen als `COL_ADJ` in `build_pdf.py` ein) |
| `src/cases.py` | erzeugt die Fallübersicht der schwierigen Zellen |

Neu bauen:
```
python3 src/rectify.py && python3 src/build_pdf.py
pdftoppm -r 150 -png garzeiten.pdf compare/pdf && python3 src/compare.py          # Seitenvergleich
pdftoppm -r 300 -png garzeiten.pdf compare/pdf300 && python3 src/align.py        # Registrierung + Differenzbilder
python3 src/measure_layout.py && python3 src/cases.py                             # Spaltenversätze, schwierige Zellen
```

Der Satz wurde anhand der Differenzbilder an das Original angeglichen: Schriftgrad 9,4 pt mit 103 % Laufweite (das Original läuft breiter als Liberation Serif), Spaltenpositionen je Seite um bis zu 5 pt korrigiert. Die Tintenüberdeckung Original/PDF liegt bei 39–47 % der PDF-Tinte; der Rest sind Glyphenform- und Strichstärkenunterschiede der Schriften, nicht Lagefehler.

Die Korrelationswerte in `schwierige_faelle` sind nur ein schwacher Hinweis: Die Nenner der Brüche sind so klein und abgerieben, dass sich die Lesarten nur um wenige Hundertstel unterscheiden. Maßgeblich ist der visuelle Vergleich im Differenzbild (z. B. ist bei Kartoffeln in der Schale und Rote Rüben der Bindestrich und ein zweiter Bruch im Original klar erkennbar, obwohl der Wert eine Einzelmenge bevorzugt).

## Unsichere Lesungen
Die Wassermengen-Brüche (⅛ l, ¼ l, ½ l) sind im Original stark abgerieben. Entschieden wurde nach der Form des Nenners (x-förmig = 8, offen = 4) und nach dem Kontext; alle nicht eindeutig lesbaren Zellen sind in der Spalte `anmerkung` markiert:
Ragout oder Gulasch (Fisch), Hähnchen ganz, Grünkohl/Rotkohl, Kartoffeln in der Schale, Kohlrouladen/Krautwickel, Rote Rüben/Bete, Schwarzwurzeln, Zwiebeln ganze sowie die erste Ziffer bei Rebhühner (3–6 Eßlöffel, analog Fasan).

Nicht reproduziert: der Bibliotheksstempel unten auf Seite 15 (die Seitenzahl 15 darunter ist im Original verdeckt und wurde ergänzt).
