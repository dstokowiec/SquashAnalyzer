# Spike F-01 — wykonalność analizy wideo

Jednorazowe skrypty spike'a `analysis-feasibility-spike` (plan: `context/changes/analysis-feasibility-spike/plan.md`). Kod nie jest częścią aplikacji; do S-02 przechodzą wyłącznie werdykt, benchmark i wnioski z raportu.

## Struktura

| Ścieżka          | Zawartość                                                          | W gicie |
| ---------------- | ------------------------------------------------------------------ | ------- |
| `benchmark/`     | manifest segmentów, ground truth                                   | tak     |
| `scripts/`       | ekstrakcja segmentów, ocena kandydatów, pomocnik ground truth      | tak     |
| `candidates/`    | skrypty kandydatów A (`cv_audio/`), B (`vlm_video/`), C (`hybrid/`) | tak     |
| `COSTS.md`       | rejestr kosztów API (budżet 50 zł)                                  | tak     |
| `media/`         | nagranie źródłowe (lub symlink) i wycięte segmenty                  | **nie** |
| `out/`           | wyniki kandydatów, oceny, pliki pośrednie                           | **nie** |

Pliki wideo i audio nigdy nie trafiają do gita (`.gitignore`).

## Środowisko

Wymagania: [uv](https://docs.astral.sh/uv/), systemowy `ffmpeg`/`ffprobe`.

```bash
cd spike/analysis
uv sync            # Python 3.12 + ultralytics, librosa, opencv-python, google-genai, pyyaml
```

Wszystkie skrypty uruchamiamy z katalogu `spike/analysis` przez `uv run python ...`.

## 1. Segmenty benchmarku

1. Uzupełnij `benchmark/segments.yaml`: nazwę nagrania (`source`), opisy strojów graczy A/B i znaczniki czasu trzech segmentów po ~5 min (początek / środek / końcówka meczu).
2. Umieść nagranie w `media/` (np. `ln -s ~/Movies/mecz.mp4 media/<source>`) albo wskaż je parametrem.
3. Wytnij segmenty:

```bash
uv run python scripts/extract_segments.py                      # media/<source>
uv run python scripts/extract_segments.py --source ~/Movies/mecz.mp4
uv run python scripts/extract_segments.py --check              # sama weryfikacja media/seg-*.mp4
```

Cięcie jest bez rekompresji (`-c copy`), więc start segmentu ląduje na klatce kluczowej — długość może się różnić od manifestu o ~1 s. Nie ma to wpływu na ocenę: ground truth liczymy na wyciętych plikach, tych samych, które dostają kandydaci.

## 2. Konwencja tożsamości graczy

Gracze to **A** i **B**, identyfikowani wyłącznie po wizualnie wykrywalnym stroju opisanym w `players` w manifeście (np. „A = biała koszulka, czarne spodenki”). Nazwiska nie istnieją dla modeli. Ten sam opis trafia do trackera (kandydat A) i do promptów VLM (kandydaci B i C). Opis musi jednoznacznie rozróżniać graczy przez cały mecz — jeśli ktoś zmienia koszulkę, segment wybieramy z fazy przed zmianą.

## 3. Protokół zliczania ground truth

Liczymy na plikach `media/seg-{id}.mp4` (nie na nagraniu źródłowym), żeby czasy były w sekundach od początku segmentu.

- **Uderzenie** = każdy kontakt rakiety z piłką, **łącznie z serwisem**.
- **Nie liczymy**: odbić piłki od ścian, podłogi i szyby; podbijania piłki ręką/rakietą między wymianami (np. podanie piłki przeciwnikowi, kozłowanie przed serwisem); zamachów bez kontaktu.
- **Uderzenie po wymianie** (piłka już „martwa”, gracz odgrywa ją dla zabawy lub podaje) — nie liczymy.
- **Czas**: moment kontaktu z dokładnością ~1 s (ocena dopasowuje zdarzenia w oknie ±1 s). Przy wątpliwym momencie cofnij klatka po klatce (np. w mpv `,` / `.`) — ścieżka audio zwykle wyraźnie wskazuje kontakt.
- **Gracz**: A lub B wg konwencji strojów. Uderzenie, którego wykonawcy nie da się ustalić (pełna okluzja), zapisz wg najlepszej oceny i dodaj komentarz `#` w CSV.
- **Kontrola**: w wymianie uderzenia alternują A/B — dwa kolejne uderzenia tego samego gracza w jednej wymianie to prawie zawsze pomyłka w notatkach (wyjątek: serwis powtórzony po błędzie / let).

Najwygodniej notować w CSV i wygenerować JSON:

```csv
segment,czas,gracz
early,0:07,A
early,0:09.5,B   # przykład
```

```bash
uv run python scripts/gt_from_csv.py benchmark/ground_truth.csv
```

Skrypt waliduje wiersze, drukuje sumy per gracz i ostrzega o możliwych duplikatach. Można też edytować `benchmark/ground_truth.json` ręcznie.

## 4. Schemat wyników i ocena

Ground truth i każdy kandydat używają tego samego schematu:

```json
{ "early": { "hits": [{ "t": 7.0, "player": "A" }, { "t": 9.5, "player": "B" }] } }
```

`t` — sekundy od początku segmentu; `player` — `"A"` lub `"B"`. Klucze zaczynające się od `_` (np. `_meta`) są ignorowane przy ocenie.

```bash
uv run python scripts/score.py out/candidate-A.json
uv run python scripts/score.py benchmark/ground_truth.json   # sanity check: 0% błędu, 100% P/R
```

`score.py` drukuje:

- **błąd % liczby uderzeń per zawodnik** per segment i łącznie — metryka progu (< 10%, liczona na sumach ze wszystkich segmentów);
- **dopasowanie zdarzeń ±1 s** (`--tol`) — precyzja i pokrycie samej detekcji oraz z atrybucją gracza; diagnostyka wychwytująca „dobrą sumę” z kompensujących się błędów.

Wynik zapisuje do `out/score-<kandydat>.json`. Kod wyjścia 0 = raport wydrukowany (niezależnie od werdyktu), 2 = błędne wejście.

## 5. Koszty

Każde płatne wywołanie API dopisuje wiersz do `COSTS.md`. Budżet spike'a: 50 zł, twardy stop.
