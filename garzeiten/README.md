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
| `src/overlay.py`, `diff/bruch_overlays.pdf` (`_1..5.png`) | alle 59 Bruch-Zellen: registriertes Original (grau) mit jeder strukturgleichen Lesart (⅛/¼/½ bzw. ⅛–¼/¼–½/⅛–½) rot darübergelegt, am Liter-l verankert; grüner Rahmen = aktuelle CSV-Lesung, „unsicher“ = in der CSV markiert. Zur manuellen Bewertung gedacht. |

Neu bauen:
```
python3 src/rectify.py && python3 src/build_pdf.py
pdftoppm -r 150 -png garzeiten.pdf compare/pdf && python3 src/compare.py          # Seitenvergleich
pdftoppm -r 300 -png garzeiten.pdf compare/pdf300 && python3 src/align.py        # Registrierung + Differenzbilder
python3 src/measure_layout.py && python3 src/cases.py                             # Spaltenversätze, schwierige Zellen
```

Der Satz wurde anhand der Differenzbilder an das Original angeglichen: Schriftgrad 9,4 pt mit 103 % Laufweite (das Original läuft breiter als Liberation Serif). Auf seitenweise Spaltenkorrekturen wurde bewusst verzichtet, damit Zeilen- und Spaltenabstände über alle vier Seiten identisch sind (`COL_ADJ` bleibt leer). Die Tintenüberdeckung Original/PDF liegt bei 39–47 % der PDF-Tinte; der Rest sind Glyphenform- und Strichstärkenunterschiede der Schriften, nicht Lagefehler.

Die Korrelationswerte in `schwierige_faelle` sind nur ein schwacher Hinweis: Die Nenner der Brüche sind so klein und abgerieben, dass sich die Lesarten nur um wenige Hundertstel unterscheiden. Maßgeblich ist der visuelle Vergleich im Differenzbild (z. B. ist bei Kartoffeln in der Schale und Rote Rüben der Bindestrich und ein zweiter Bruch im Original klar erkennbar, obwohl der Wert eine Einzelmenge bevorzugt).

## Satz-Details nach Vorbild des Originals
- Garzeiten (und Einweichzeiten) sind wie im Original um eine feste Gedankenstrich-Position gesetzt: erste Zahl rechtsbündig davor, zweite rechtsbündig in einem zweistelligen Feld dahinter („6– 8“ unter „20–25“), Einzelwerte unter der Einerstelle. Zehner stehen so über Zehnern. In der CSV stehen die Zeiten ohne Ausrichtungs-Leerzeichen (`6–8`).
- Kopfzeile „eingeweicht / nicht eingeweicht“ auf Seite 15 ist wie im Original kleiner gesetzt (78 %).
- Zu lange Zellen werden automatisch in der Laufweite verengt, statt in die Nachbarspalte zu laufen (Namen bis zur Garzeit- bzw. Einweich-Spalte, Einsatz bis zur Wasser-Spalte, Wassermenge bis knapp über den Tabellenrand, wie es das Original bei „mit Wasser bedecken“ auch tut).
- Wassermengen, die im Original so abgerieben sind, dass die Lesung unsicher bleibt, sind im PDF **rot unterstrichen** (Fußnote auf Seite 15). In der CSV beginnt ihre `anmerkung` mit `UNSICHER:`.

## Unsichere Lesungen
Die Wassermengen-Brüche (⅛ l, ¼ l, ½ l) sind im Original stark abgerieben. Entschieden wurde nach der Form des Nenners (x-förmig = 8, offen = 4) und nach dem Kontext, anschließend anhand der Overlay-Blätter manuell geprüft. Dabei bestätigt bzw. korrigiert: Steinobst, Kastanien und Kernobst → ⅛ l; Kartoffeln in der Schale ⅛–¼ l und Grünkohl/Rotkohl ¼ l bestätigt.
Weiterhin unsicher (rot unterstrichen): Ragout oder Gulasch (Fisch) ⅛ l, Hähnchen ganz ⅛ l, Kohlrouladen/Krautwickel ⅛–¼ l, Rote Rüben/Bete ¼–½ l, Sauerkraut ¼ l (im Original in der Einsatz-Spalte gesetzt, hier in der Wasser-Spalte), Schwarzwurzeln ¼ l, Zwiebeln ganze ¼ l sowie die erste Ziffer bei Rebhühner (3–6 Eßlöffel, analog Fasan).

Nicht reproduziert: der Bibliotheksstempel unten auf Seite 15 (die Seitenzahl 15 darunter ist im Original verdeckt und wurde ergänzt).
