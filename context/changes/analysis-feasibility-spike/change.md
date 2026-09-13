---
change_id: analysis-feasibility-spike
title: "Spike wykonalności analizy wideo (F-01)"
status: implementing
created: 2026-08-07
updated: 2026-09-13
roadmap_id: F-01
---

# Change: analysis-feasibility-spike

Walidacja podejścia do automatycznej analizy wideo squasha (klasyczne CV+audio vs VLM z natywnym wideo vs hybryda) na referencyjnym nagraniu z ręcznym ground truth. Progi zaliczenia: błąd licznika uderzeń per zawodnik < 10% ORAZ koszt analizy pełnego meczu ≤ 2 zł. Wynik odblokowuje S-02 (analiza) i S-06 (heatmapa pozycji) z roadmapy.

Artefakty:

- `plan.md` — szczegółowy plan implementacji spike'a
- `plan-brief.md` — dwustronicowy brief planu
- `report.md` — raport decyzyjny (powstaje w fazie 5)
