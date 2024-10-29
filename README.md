Dieses Projekt implementiert:

1. einen Simulator, der in Kombination mit der CPEE-Engine (https://cpee.org), basierend auf einer Konfigurationsdatei, ein Problem simulieren kann.
2. einen Planner, der für ein spezifisches Healthcare-Problem (https://sites.google.com/view/bpo2024/competition) Patientenzeiten basierend auf einem genetischen Algorithmus plant.
3. einen PatientSpawner, der es ermöglicht, CPEE-Instanzen zu generieren, um das Healthcare-Problem zu simulieren.
4. einen Logger.
5. eine Konfigurationsdatei für das Healthcare-Problem.

Voraussetzungen:
-Python 3.8 oder höher
-bottle (Webserver)
-requests (HTTP-Anfragen)
-numpy (mathematische Funktionen und Wahrscheinlichkeitsberechnungen)
-Bearbeitung der Konfigurationsdatei (für den Simulator ist eine Konfigurationsdatei erforderlich, ein Beispiel für das Healthcare-Problem ist im Code enthalten)

Anleitung zum Erstellen / Bearbeiten der Konfigurationsdatei:

1. Die Konfigurationsdatei besteht aus einem Dictionary namens events.
2. Jedes gewünschte Event wird als Schlüssel in diesem Dictionary hinzugefügt.
3. Jedes dieser Events benötigt folgende Schlüssel:
   -Capacity: Eine Liste von Kapazitätsregeln, die festlegt, zu welchen Zeiten (verschiedene Tage und Stunden, Tag 0 entspricht Montag) das Event Kapazitäten hat. Kapazitätsregeln werden von oben nach unten priorisiert (im Falle von Überschneidungen). Der Standardwert für nicht definierte Zeiten ist 0.
   -Dependencies: Eine Liste von Events, die chronologisch vor dem aktuellen Event liegen müssen.
   -Bookings: Speichert abgeschlossene Buchungen für das Event (zur Initialisierung leer lassen).
   -Active Bookings: Speichert aktive Buchungen für das Event (zur Initialisierung leer lassen).

Starten der Simulation:

1. Wechseln Sie in das Verzeichnis mit dem Code:
   cd Pfad-zu/Sim_Code
2. Starten Sie den Simulator (er benötigt als Parameter die gewünschte Simulationsdauer in Minuten, 525600 entspricht 1 Jahr):
   python3 Simulator.py 525600
3. Starten Sie den PatientSpawner (er benötigt als Parameter die gewünschte Simulationsdauer in Minuten, 525600 entspricht 1 Jahr):
   python3 PatientSpawner.py 525600
