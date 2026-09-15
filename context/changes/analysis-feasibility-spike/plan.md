# Spike wykonalności analizy wideo — Implementation Plan

## Overview

Spike walidacyjny dla F-01 z roadmapy: zmierzyć na wspólnym benchmarku ground-truth trzy podejścia do automatycznej analizy nagrania meczu squasha (stałe ujęcie zza tylnej szyby) i wydać werdykt, które podejście przechodzi oba progi: **błąd licznika uderzeń per zawodnik < 10%** ORAZ **koszt analizy pełnego meczu ≤ 2 zł**. Dodatkowo: jakościowa walidacja ciągłego śledzenia pozycji graczy (podstawa heatmapy S-06). Werdykt odblokowuje planowanie S-02 i S-06.

Kandydaci:

- **A — CV+audio lokalnie**: YOLO tracking graczy + homografia kortu + detekcja onsetów audio + heurystyka atrybucji. Koszt ~0 zł.
- **B — VLM z natywnym wideo**: Gemini (rodzina Flash-Lite), segmenty wideo+audio przez Files API. Koszt mierzony, wstępnie ~0.15–0.45 zł/mecz.
- **C — Hybryda**: onsety audio z A wskazują momenty-kandydatów; VLM klasyfikuje wyłącznie te momenty (klatki wokół onsetu). Koszt groszowy.

## Current State Analysis

- Repo to świeży scaffold Astro/Supabase/Cloudflare — **spike nie dotyka aplikacji**; żyje w katalogu `spike/` (skrypty jednorazowe, decyzja z wywiadu: skrypty + raport + benchmark, nie zalążek modułu).
- Użytkownik ma zgodne nagranie (stałe ujęcie zza szyby, cały kort, pełny mecz, plik rzędu GB) — nagranie NIE trafia do gita.
- Brak jakiegokolwiek kodu analizy, brak lessons.md, brak wcześniejszych spike'ów.
- Blocker roadmapy to `skills` — spike jest jednocześnie nauką tej warstwy; forma skryptowa ma sprzyjać szybkim iteracjom.

## Desired End State

1. Zamrożony benchmark: 3 segmenty po ~5 min z różnych faz meczu + ręcznie zliczone uderzenia per zawodnik (`ground_truth.json`) + deterministyczny skrypt oceny (`score.py`). Benchmark jest wielokrotnego użytku — posłuży przy odbiorze S-02.
2. Trzy uruchamialne skrypty-kandydaci, każdy produkujący wynik w tym samym schemacie JSON co ground truth.
3. Raport decyzyjny `context/changes/analysis-feasibility-spike/report.md`: tabela porównawcza (błąd per zawodnik per segment, ekstrapolowany koszt pełnego meczu, werdykt jakościowy pozycji), wybrane podejście LUB raport częściowy z opcjami, gdy nic nie przeszło progów (decyzja wraca do użytkownika).
4. Rejestr kosztów API (`COSTS.md`) z sumą ≤ 50 zł.
5. Roadmapa: Open Question #1 domknięte (pułap 2 zł potwierdzony pomiarem albo z wnioskiem o rewizję).

Weryfikacja końcowa: `score.py` odtwarza wszystkie liczby z raportu z zapisanych plików wynikowych.

### Key Discoveries:

- **Modele Claude nie przyjmują wideo** (tylko obrazy) — czysty kandydat VLM musi używać Gemini z natywnym wejściem wideo; modele obrazowe wchodzą tylko w hybrydzie (referencja claude-api).
- **Gemini wideo**: ~300 tok/s (domyślna rozdzielczość) / ~100 tok/s (niska), próbkowanie 1 FPS, audio w cenie (32 tok/s). 60 min ≈ $0.108 (2.5 Flash-Lite, default) ≈ 0.4 zł — mieści się w pułapie. Files API: limit 2 GB/plik, pliki żyją 48 h.
- **1 FPS to ryzyko dla detekcji uderzeń** — benchmark F3Set: multimodalne LLM-y słabo łapią szybkie, pod-sekundowe zdarzenia w sportach rakietowych. Sygnałem ratunkowym może być ścieżka audio — prompt musi jawnie kazać jej użyć.
- **CV**: Ultralytics YOLO11/26 z wbudowanym trackingiem (BoT-SORT/ByteTrack) działa na Apple Silicon (MPS) szybciej niż real-time; mapowanie pozycji na kort = jednorazowa homografia z 4 kliknięterogów (kamera stała).
- **Audio onset detection to uznana technika** — praca squashowa (PLOS ONE 2018, Hajdú-Szücs) potwierdza wysoką precyzję dla uderzeń rakietą, ale ostrzega: pogłos szklanego kortu, słabe sygnały odbić od podłogi/szyby, mylenie odbicia od ściany z uderzeniem rakietą. Tam użyto macierzy 6 mikrofonów — my mamy 1 mikrofon telefonu: to główne ryzyko kandydata A.
- **Śledzenie piłki w squashu to znany trudny problem** (mała, szybka, rozmyta; wymaga specjalizowanych modeli klasy TrackNet bez gotowca dla squasha) — świadomie POZA spike'iem.
- **Naprzemienność uderzeń**: w wymianie squashowej uderzenia ściśle alternują między graczami — silny prior dla atrybucji, łamany tylko przez błędy detekcji.
- Istniejące projekty open-source dla squasha: martwe, żaden nie dowiózł atrybucji uderzeń — nie ma gotowca.

## What We're NOT Doing

- Śledzenie piłki i miejsce odbicia piłki (uwaga zakresowa PRD — v2).
- Klasyfikacja rodzaju uderzenia (PRD Non-Goal).
- Kod produkcyjny: żadnych zmian w `src/`, żadnej integracji z aplikacją, uploadem, kolejkami (to S-01/F-02/S-02).
- Trening/fine-tuning modeli — wyłącznie gotowe modele i API.
- Ilościowa walidacja pozycji (próg w metrach) — decyzja z wywiadu: walidacja jakościowa nakładką trajektorii.
- Obsługa innych ujęć kamery niż założone (PRD Non-Goal).

## Implementation Approach

Wszystko w `spike/analysis/` (Python + uv), media i wyniki poza gitem. Wspólny kontrakt danych: każdy kandydat emituje JSON w schemacie ground truth, oceniany jednym skryptem `score.py` — dzięki temu porównanie jest uczciwe, a liczby w raporcie odtwarzalne. Kolejność kandydatów: A przed C (C konsumuje onsety z A); B niezależny. Każde wywołanie API dopisuje wiersz do `COSTS.md`; przekroczenie 50 zł = twardy stop i werdykt z danych częściowych. Porażka obu progów w każdym kandydacie NIE jest porażką spike'a — raport częściowy z opcjami (podnieść pułap / degradować zakres / inne nagranie) i decyzja wraca do użytkownika.

## Critical Implementation Details

**Konwencja tożsamości graczy.** Ground truth, tracking i VLM muszą identyfikować graczy tym samym, wizualnie wykrywalnym kluczem — kolorem stroju (np. "A = jasna koszulka"), zapisanym w manifeście benchmarku. Nazwiska nie istnieją dla modeli. Częste okluzje (gracze w squashu bywają ciasno obok siebie) będą powodować podmiany ID trackera — atrybucja nie może polegać wyłącznie na ID toru, weryfikacją podmian jest nakładka trajektorii.

**Dopasowanie uderzeń w ocenie.** `score.py` liczy nie tylko błąd sumaryczny per zawodnik (metryka progu z PRD), ale też dopasowanie zdarzeń w oknie ±1 s (precyzja/pokrycie) — bez tego kandydat może mieć "dobrą sumę" z kompensujących się błędów, a to zafałszowałoby werdykt.

**Gemini i pełny mecz.** 60 min przy domyślnej rozdzielczości ≈ 1.08M tokenów — na krawędzi kontekstu 1M; produkcyjnie analiza szłaby w kawałkach. Spike operuje na segmentach 5 min, ale raport musi odnotować konieczność chunkowania w S-02. Prompt do Gemini ma jawnie polecać użycie ścieżki audio do lokalizacji uderzeń (wizualnie 1 FPS ich nie zobaczy).

**Ekstrapolacja kosztu.** Próg dotyczy pełnego meczu; mierzymy koszt na segmentach i ekstrapolujemy per minutę × długość meczu z nagrania referencyjnego. Dla A koszt ≈ 0 zł (lokalny compute) — w raporcie odnotować czas przetwarzania (NFR < 1h).

## Phase 1: Benchmark i fundament

### Overview

Powstaje wspólna miara wszystkich kandydatów: segmenty, ground truth, skrypt oceny, rejestr kosztów. Bez tej fazy żaden pomiar nie jest wiarygodny.

### Changes Required:

#### 1. Struktura spike'a i środowisko

**File**: `spike/analysis/` (nowy katalog: `README.md`, `pyproject.toml`, `.gitignore`, `COSTS.md`)

**Intent**: Samodzielne środowisko Python (uv, Python 3.12) z zależnościami: `ultralytics`, `librosa`, `opencv-python`, `google-genai`; systemowy `ffmpeg`. README opisuje: jak uruchomić każdy skrypt, protokół zliczania ground truth, konwencję tożsamości graczy. `.gitignore` wyklucza `media/` i `out/` (segmenty, wideo, wyniki pośrednie — commitujemy skrypty, manifest, ground truth i raporty, nigdy plików wideo). `COSTS.md` startuje z budżetem 50 zł i pustą tabelą (data, model, tokeny, koszt zł, suma narastająco).

**Contract**: Katalog `spike/analysis/` z podkatalogami `benchmark/`, `scripts/`, `candidates/`, `media/` (gitignored), `out/` (gitignored).

#### 2. Manifest segmentów i ekstrakcja

**File**: `spike/analysis/benchmark/segments.yaml`, `spike/analysis/scripts/extract_segments.py`

**Intent**: Manifest deklaruje plik źródłowy (nazwa, nie zawartość), znaczniki czasu trzech segmentów ~5 min (początek/środek/końcówka meczu) i konwencję tożsamości graczy (kolor stroju → etykieta A/B). Skrypt tnie segmenty ffmpegiem (bez rekompresji, `-c copy`) do `media/` — segmenty są odtwarzalne z nagrania źródłowego + manifestu, więc nie muszą być w gicie.

**Contract**: `segments.yaml`: `source`, `players: {A: <opis wizualny>, B: <opis wizualny>}`, `segments: [{id, start, end}]`. Wyjście: `media/seg-{id}.mp4`.

#### 3. Ground truth i skrypt oceny

**File**: `spike/analysis/benchmark/ground_truth.json`, `spike/analysis/scripts/score.py`

**Intent**: Użytkownik ręcznie zlicza uderzenia oglądając segmenty (protokół w README: liczy się każdy kontakt rakieta–piłka, w tym serwis; zapisujemy czas z dokładnością ~1 s i gracza). `score.py` porównuje plik kandydata z ground truth: błąd % liczby uderzeń per zawodnik per segment i łącznie (metryka progu < 10%) oraz dopasowanie zdarzeń w oknie ±1 s (precyzja/pokrycie — diagnostyka). Deterministyczny, czyta dwa JSON-y, drukuje tabelę i zapisuje wynik do `out/`.

**Contract**: Wspólny schemat JSON dla ground truth i kandydatów: `{segment_id: {hits: [{t: <sekundy od startu segmentu>, player: "A"|"B"}]}}`. `score.py <candidate.json>` — kod wyjścia 0, raport na stdout.

### Success Criteria:

#### Automated Verification:

- Środowisko instaluje się czysto: `uv sync` w `spike/analysis/`
- `extract_segments.py` produkuje 3 pliki `media/seg-*.mp4` zgodne z manifestem
- `score.py` uruchomiony na spreparowanym pliku kandydata (kopia ground truth) raportuje błąd 0% i pokrycie 100%
- `git status` nie pokazuje żadnych plików wideo jako nietrackowanych do dodania (gitignore działa)

#### Manual Verification:

- Ground truth zliczony dla 3 segmentów, per zawodnik, wg protokołu z README (~1 h pracy użytkownika)
- Użytkownik potwierdza protokół zliczania i konwencję tożsamości graczy (kolor stroju)

**Implementation Note**: Po zakończeniu fazy i przejściu automatycznej weryfikacji zatrzymaj się — ground truth to praca ręczna użytkownika i warunek wszystkich dalszych faz.

---

## Phase 2: Kandydat A — CV+audio lokalnie

### Overview

Pipeline lokalny: śledzenie graczy (YOLO + tracking, MPS), pozycje na korcie (homografia), momenty uderzeń (onsety audio), atrybucja (naprzemienność + pozycje). Produkt uboczny: trajektorie pozycji — walidacja jakościowa pod heatmapę S-06 i onsety wielokrotnego użytku dla kandydata C.

### Changes Required:

#### 1. Kalibracja kortu

**File**: `spike/analysis/candidates/cv_audio/calibrate.py`

**Intent**: Jednorazowe kliknięcie 4 narożników kortu na klatce z segmentu → macierz homografii zapisana do pliku; wspólna dla wszystkich segmentów (kamera stała). Rzut pozycji gracza = środek dolnej krawędzi bounding boxa przez homografię.

**Contract**: Wyjście `out/homography.json` (macierz 3×3 + użyte punkty piksele→metry kortu 6.4×9.75 m).

#### 2. Detekcja i śledzenie graczy

**File**: `spike/analysis/candidates/cv_audio/track_players.py`

**Intent**: Ultralytics YOLO (klasa person) w trybie `track` (BoT-SORT) na każdym segmencie, urządzenie MPS; przypisanie torów do etykiet A/B po kolorze stroju z manifestu (dominujący kolor górnej części boxa), odporne na podmiany ID trackera. Wyjście: pozycje kortowe obu graczy w czasie.

**Contract**: `out/seg-{id}.positions.json`: `[{t, A: [x,y]|null, B: [x,y]|null}]` w metrach kortu, częstotliwość ≥ 5 Hz.

#### 3. Onsety audio

**File**: `spike/analysis/candidates/cv_audio/audio_onsets.py`

**Intent**: Ekstrakcja audio z segmentu (ffmpeg), detekcja onsetów (librosa, wariant superflux) z progiem strojonym na pierwszym segmencie; wyjście to momenty-kandydaci uderzeń. Znane ryzyko: pogłos szklanego kortu i odbicia od ścian — strojenie progu i minimalnego odstępu między onsetami jest głównym pokrętłem tej fazy.

**Contract**: `out/seg-{id}.onsets.json`: `[{t, strength}]`. Konsumowane też przez kandydata C (kontrakt między fazami 2 i 4).

#### 4. Atrybucja i wynik kandydata

**File**: `spike/analysis/candidates/cv_audio/attribute.py`

**Intent**: Złączenie onsetów z pozycjami w heurystykę atrybucji: prior naprzemienności uderzeń w wymianie + pozycje graczy w momencie onsetu (szczegół heurystyki do iteracji w implementacji — plan nie przesądza). Wyjście w schemacie benchmarku, ocena przez `score.py`.

**Contract**: `out/candidate-A.json` w schemacie benchmarku.

#### 5. Nakładka trajektorii (walidacja pozycji)

**File**: `spike/analysis/candidates/cv_audio/overlay.py`

**Intent**: Render wideo segmentu z naniesionymi pozycjami/trajektoriami obu graczy (etykiety A/B) — użytkownik ocenia wzrokowo "czy punkt jest tam, gdzie biega gracz" (decyzja z wywiadu: walidacja jakościowa, dokładność rzędu metra wystarcza dla heatmapy).

**Contract**: `out/seg-{id}.overlay.mp4`.

### Success Criteria:

#### Automated Verification:

- Pipeline przechodzi end-to-end na 3 segmentach: `track_players.py`, `audio_onsets.py`, `attribute.py` produkują pliki kontraktowe
- `score.py out/candidate-A.json` drukuje raport błędu (wartość — do oceny ręcznej)
- Czas przetwarzania segmentu zmierzony i zapisany w `out/` (ekstrapolacja do NFR < 1h w fazie 5)

#### Manual Verification:

- Nakładka trajektorii obejrzana dla ≥ 1 segmentu: pozycje odpowiadają ruchowi graczy, etykiety A/B nie zamieniają się trwale po okluzjach
- Wynik błędu per zawodnik omówiony (przechodzi/nie przechodzi progu 10% — bez iterowania w nieskończoność: maks. kilka rund strojenia progu onsetów)

**Implementation Note**: Po tej fazie zatrzymaj się na ocenę użytkownika (nakładka + błąd) przed przejściem dalej.

---

## Phase 3: Kandydat B — VLM z natywnym wideo

### Overview

Gemini Flash-Lite analizuje segmenty jako natywne wideo (obraz 1 FPS + audio). Mierzymy błąd i rzeczywisty koszt z metadanych odpowiedzi; ekstrapolujemy na pełny mecz.

### Changes Required:

#### 1. Uruchomienie i pomiar

**File**: `spike/analysis/candidates/vlm_video/run_gemini.py`

**Intent**: Upload segmentu przez Gemini Files API, prompt żądający listy uderzeń per gracz (etykiety wg opisu stroju z manifestu) ze znacznikami czasu, w ustrukturyzowanym JSON; jawne polecenie użycia ścieżki audio do lokalizacji momentów uderzeń. Dwa warianty przebiegu: `media_resolution` niska i domyślna. Model startowy: najtańszy z rodziny Flash-Lite; droższy wariant Flash tylko jeśli tani nie przechodzi progu błędu a budżet pozwala. Koszt liczony z `usage_metadata` odpowiedzi i dopisywany do `COSTS.md` po każdym wywołaniu.

**Contract**: `out/candidate-B-{low|default}.json` w schemacie benchmarku + wpisy w `COSTS.md`. Ekstrapolacja: koszt/minuta × długość pełnego meczu, zapisana w `out/candidate-B.cost.json`.

### Success Criteria:

#### Automated Verification:

- Przebiegi na 3 segmentach w obu rozdzielczościach kończą się plikami kontraktowymi
- `score.py` raportuje błąd dla obu wariantów
- `COSTS.md` zawiera wpisy wszystkich wywołań; suma narastająca ≤ 50 zł

#### Manual Verification:

- Przegląd błędów i decyzja o ewentualnej iteracji promptu (maks. kilka rund — budżet i timebox)
- Ekstrapolowany koszt pełnego meczu skonfrontowany z progiem 2 zł

**Implementation Note**: Po tej fazie zatrzymaj się na przegląd wyników i kosztów z użytkownikiem.

---

## Phase 4: Kandydat C — Hybryda (onsety audio + VLM na momentach)

### Overview

Onsety z fazy 2 wskazują momenty-kandydatów; VLM widzi tylko krótkie okna klatek wokół onsetu i klasyfikuje: uderzenie gracza A / gracza B / odbicie od ściany / inne. Adresuje słabość A (mylenie odbić z uderzeniami) za groszowy koszt.

### Changes Required:

#### 1. Klasyfikacja momentów

**File**: `spike/analysis/candidates/hybrid/classify_onsets.py`

**Intent**: Dla każdego onsetu z `out/seg-{id}.onsets.json` wyciąć 2–3 klatki wokół momentu (ffmpeg), wysłać do taniego modelu obrazowego (Gemini Flash-Lite jako obrazy; batchowanie wielu onsetów w jednym wywołaniu) z pytaniem o klasę zdarzenia i gracza (po stroju). Z klasyfikacji budowany jest wynik w schemacie benchmarku. Koszt per segment mierzony i ekstrapolowany (skaluje się z liczbą onsetów, nie długością wideo).

**Contract**: `out/candidate-C.json` + wpisy w `COSTS.md` + `out/candidate-C.cost.json`.

### Success Criteria:

#### Automated Verification:

- Przebieg na 3 segmentach produkuje plik kontraktowy; `score.py` raportuje błąd
- `COSTS.md` aktualny; suma ≤ 50 zł

#### Manual Verification:

- Przegląd błędu względem A i B; ocena, czy klasyfikacja VLM faktycznie odsiewa odbicia od ścian (porównanie precyzji z kandydatem A)

**Implementation Note**: Po tej fazie zatrzymaj się — komplet danych do werdyktu.

---

## Phase 5: Werdykt i raport decyzyjny

### Overview

Zamknięcie spike'a: porównanie, decyzja, zamrożenie benchmarku, domknięcie pytań roadmapy. Porażka progów to też prawomocny wynik — wtedy raport częściowy z opcjami i decyzja wraca do użytkownika.

### Changes Required:

#### 1. Raport decyzyjny

**File**: `context/changes/analysis-feasibility-spike/report.md`

**Intent**: Tabela porównawcza (błąd per zawodnik per segment i łącznie, precyzja/pokrycie ±1 s, ekstrapolowany koszt pełnego meczu, czas przetwarzania, werdykt jakościowy pozycji, odporność/ryzyka) + werdykt: wybrane podejście dla S-02/S-06 z uzasadnieniem, LUB — jeśli żaden kandydat nie przeszedł obu progów — najlepsze osiągnięte wyniki i opcje decyzyjne (podnieść pułap / degradować zakres, np. licznik łączny / poprawić nagranie). Raport odnotowuje też: konieczność chunkowania wideo w S-02 (limit kontekstu Gemini), wnioski o wiarygodności śledzenia pozycji dla S-06, rzeczywisty łączny koszt spike'a.

**Contract**: Wszystkie liczby w raporcie odtwarzalne przez `score.py` z zapisanych plików `out/candidate-*.json`.

#### 2. Zamrożenie benchmarku i aktualizacja roadmapy

**File**: `spike/analysis/README.md`, `context/foundation/roadmap.md`

**Intent**: README dostaje sekcję "Benchmark odbiorczy S-02" (jak odtworzyć segmenty i przegonić kandydata finalnego przez `score.py` przy odbiorze S-02). W roadmapie: Open Roadmap Question #1 oznaczone jako rozstrzygnięte (pułap 2 zł potwierdzony pomiarem albo wniosek o rewizję — wtedy decyzja użytkownika), zaktualizowane pole Unknowns/Risk w F-01. Statusu F-01 na `done` NIE zmieniamy — to robi `/10x-archive`.

**Contract**: Edycja w miejscu `## Open Roadmap Questions` w roadmapie; sekcja benchmarku w README spike'a.

### Success Criteria:

#### Automated Verification:

- `score.py` uruchomiony na wszystkich `out/candidate-*.json` odtwarza liczby z tabeli raportu
- `COSTS.md`: suma końcowa ≤ 50 zł

#### Manual Verification:

- Użytkownik akceptuje werdykt (albo podejmuje decyzję z opcji raportu częściowego)
- Roadmapa odzwierciedla rozstrzygnięcie OQ#1

---

## Testing Strategy

### Unit Tests:

- Spike świadomie bez testów jednostkowych — benchmark JEST testem: deterministyczny `score.py` na zamrożonym ground truth.
- Sanity check `score.py`: ground truth vs samego siebie = 0% błędu (kryterium fazy 1).

### Integration Tests:

- End-to-end każdego kandydata: segmenty → plik wynikowy → `score.py` (kryteria automatyczne faz 2–4).

### Manual Testing Steps:

1. Obejrzeć nakładkę trajektorii (faza 2) — zgodność pozycji i stabilność etykiet A/B.
2. Wyrywkowo porównać kilka wykrytych uderzeń kandydata finalnego z wideo (podgląd momentów z `out/`).
3. Zweryfikować kilka wpisów `COSTS.md` z konsolą billingową dostawcy.

## Performance Considerations

- Kandydat A: pomiar czasu przetwarzania segmentu → ekstrapolacja na pełny mecz vs NFR < 1h (raport).
- Kandydat B: limit kontekstu wymusza chunkowanie pełnego meczu w produkcji — zapisane w raporcie jako wymaganie projektowe S-02.

## Migration Notes

Nie dotyczy — spike nie zmienia aplikacji ani danych. Kod spike'a jest jednorazowy; do S-02 przechodzi wyłącznie werdykt, benchmark i wnioski z raportu.

## References

- Roadmapa F-01: `context/foundation/roadmap.md` (Unlocks: S-02, S-06; OQ#1)
- PRD v2: `context/foundation/prd.md` (Business Logic, NFR wiarygodność/koszt/czas, FR-009)
- Badania (sesja planowania): Gemini video ~300 tok/s, 1 FPS, Files API 2 GB — ai.google.dev/gemini-api/docs/video-understanding, /pricing, /files; F3Set (VLM vs szybkie zdarzenia); Ultralytics track mode — docs.ultralytics.com/modes/track; audio w squashu — PLOS ONE 2018 (journals.plos.org/plosone/article?id=10.1371/journal.pone.0194394); TrackNet (piłka = trudny problem, poza zakresem)

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles.

### Phase 1: Benchmark i fundament

#### Automated

- [x] 1.1 Środowisko instaluje się czysto (`uv sync`)
- [ ] 1.2 `extract_segments.py` produkuje 3 segmenty zgodne z manifestem
- [x] 1.3 `score.py` na kopii ground truth raportuje 0% błędu i 100% pokrycia
- [x] 1.4 Gitignore wyklucza pliki wideo (czysty `git status`)

#### Manual

- [ ] 1.5 Ground truth zliczony dla 3 segmentów per zawodnik
- [ ] 1.6 Protokół zliczania i konwencja tożsamości graczy potwierdzone

### Phase 2: Kandydat A — CV+audio lokalnie

#### Automated

- [ ] 2.1 Pipeline end-to-end na 3 segmentach produkuje pliki kontraktowe
- [ ] 2.2 `score.py` raportuje błąd dla candidate-A
- [ ] 2.3 Czas przetwarzania segmentu zmierzony i zapisany

#### Manual

- [ ] 2.4 Nakładka trajektorii zweryfikowana (pozycje + stabilność etykiet A/B)
- [ ] 2.5 Wynik błędu omówiony względem progu 10%

### Phase 3: Kandydat B — VLM z natywnym wideo

#### Automated

- [ ] 3.1 Przebiegi na 3 segmentach w obu rozdzielczościach zakończone plikami kontraktowymi
- [ ] 3.2 `score.py` raportuje błąd dla obu wariantów
- [ ] 3.3 `COSTS.md` kompletny, suma ≤ 50 zł

#### Manual

- [ ] 3.4 Przegląd błędów i decyzja o iteracji promptu
- [ ] 3.5 Ekstrapolowany koszt pełnego meczu skonfrontowany z progiem 2 zł

### Phase 4: Kandydat C — Hybryda

#### Automated

- [ ] 4.1 Przebieg na 3 segmentach produkuje plik kontraktowy; `score.py` raportuje błąd
- [ ] 4.2 `COSTS.md` aktualny, suma ≤ 50 zł

#### Manual

- [ ] 4.3 Porównanie z A i B; ocena odsiewu odbić od ścian

### Phase 5: Werdykt i raport decyzyjny

#### Automated

- [ ] 5.1 `score.py` odtwarza liczby z tabeli raportu ze wszystkich `out/candidate-*.json`
- [ ] 5.2 `COSTS.md`: suma końcowa ≤ 50 zł

#### Manual

- [ ] 5.3 Werdykt zaakceptowany przez użytkownika (lub decyzja z opcji raportu częściowego)
- [ ] 5.4 Roadmapa odzwierciedla rozstrzygnięcie OQ#1
