# Spike wykonalności analizy wideo — Plan Brief

> Full plan: `context/changes/analysis-feasibility-spike/plan.md`

## What & Why

Cały produkt Squash Analyzer wisi na jednym niepotwierdzonym założeniu: że automatyczna analiza nagrania policzy uderzenia per zawodnik z błędem < 10% i zmieści się w koszcie ≤ 2 zł za mecz. Spike mierzy trzy podejścia na wspólnym benchmarku ground-truth i wydaje werdykt, który odblokowuje plastry S-02 (analiza) i S-06 (heatmapa pozycji).

## Starting Point

Świeży scaffold Astro/Supabase bez żadnego kodu analizy; spike nie dotyka aplikacji i żyje w `spike/analysis/` (Python). Użytkownik ma zgodne nagranie referencyjne (stałe ujęcie zza szyby, pełny mecz, plik GB — poza gitem).

## Desired End State

Zamrożony benchmark (3 segmenty × 5 min + ręczny ground truth + deterministyczny `score.py`, wielokrotnego użytku przy odbiorze S-02), trzy zmierzone podejścia i raport decyzyjny w `report.md`: wybrane podejście z liczbami, albo raport częściowy z opcjami, gdy nic nie przeszło progów. Roadmapowe Open Question #1 (pułap kosztowy) domknięte pomiarem.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) |
| --- | --- | --- |
| Progi zaliczenia | błąd < 10% ORAZ ≤ 2 zł/mecz | Guardrail PRD + wybrany agresywny pułap (bezpieczny przy skali 100×); domyka OQ#1 roadmapy |
| Ground truth | próbki 3×5 min (początek/środek/końcówka) | ~1 h ręcznej pracy, łapie zmienność faz meczu, wystarczające dla progu 10% |
| Pole porównania | wszystkie trzy podejścia równolegle | Pełny obraz decyzyjny + maksimum nauki nieznanej warstwy (blocker: umiejętności) |
| Walidacja pozycji (S-06) | jakościowa nakładka trajektorii | Heatmapa to agregat — dokładność rzędu metra wystarcza, zero drugiej rundy tagowania |
| Budżet eksperymentów | ≤ 50 zł, rejestr w COSTS.md | Twardy stop; przy zmierzonych cenach (Gemini ~0.15–0.45 zł/mecz) w pełni wystarczający |
| Artefakt | skrypty + raport + zamrożony benchmark | Spike zostaje spike'iem; kod jednorazowy, benchmark przechodzi do odbioru S-02 |
| Porażka progów | timebox → raport częściowy → decyzja użytkownika | Porażka to też wynik; opcje: podnieść pułap / degradować zakres / inne nagranie |
| VLM dla wideo | Gemini Flash-Lite (natywne wideo+audio) | Modele Claude nie przyjmują wideo; Gemini mieści pełny mecz w ~0.15–0.45 zł |

## Scope

**In scope:** benchmark + ground truth; kandydat A (YOLO tracking + homografia + onsety audio + atrybucja), B (Gemini natywne wideo), C (hybryda: onsety → VLM klasyfikuje momenty); pomiar błędu, kosztu i czasu; jakościowa walidacja trajektorii; raport decyzyjny; domknięcie OQ#1.

**Out of scope:** śledzenie piłki i miejsca odbicia (v2), klasyfikacja rodzaju uderzenia (non-goal), jakikolwiek kod produkcyjny/integracja z aplikacją, trening modeli, ilościowy próg dla pozycji.

## Architecture / Approach

Wspólny kontrakt danych: każdy kandydat emituje JSON w schemacie ground truth (`{hits: [{t, player}]}`), oceniany jednym `score.py` (błąd sumaryczny per zawodnik + dopasowanie zdarzeń ±1 s). Gracze identyfikowani wizualnie (kolor stroju z manifestu) — jedyny klucz czytelny dla CV i VLM. A liczy lokalnie (~0 zł, pozycje = darmowy fundament heatmapy), B mierzy natywne wideo Gemini (ryzyko: 1 FPS nie widzi uderzeń — ratunkiem ścieżka audio), C łączy precyzyjny timing audio z tanią klasyfikacją VLM tylko w momentach-kandydatach.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Benchmark i fundament | segmenty + ground truth + score.py + rejestr kosztów | rzetelność ręcznego zliczania (protokół w README) |
| 2. Kandydat A: CV+audio | pipeline lokalny + trajektorie + onsety | pogłos szklanego kortu: odbicia od ścian mylone z uderzeniami (1 mikrofon) |
| 3. Kandydat B: VLM wideo | pomiar błędu i kosztu Gemini | 1 FPS może nie widzieć uderzeń (literatura: F3Set) |
| 4. Kandydat C: hybryda | klasyfikacja momentów przez VLM | dziedziczy pominięte onsety z A (co audio nie wykryło, VLM nie zobaczy) |
| 5. Werdykt i raport | report.md + zamrożony benchmark + aktualizacja roadmapy | dyscyplina zamknięcia mimo pokusy „jeszcze jednej iteracji" |

**Prerequisites:** nagranie referencyjne dostępne lokalnie; klucz API Google (Gemini); ffmpeg + uv na maszynie; ~1 h użytkownika na ground truth (faza 1) i przeglądy między fazami.
**Estimated effort:** ~4–6 sesji przez 5 faz; praca ręczna użytkownika skoncentrowana w fazie 1 i w przeglądach.

## Open Risks & Assumptions

- Audio z jednego mikrofonu telefonu może nie wystarczyć do wiarygodnych onsetów (praca squashowa używała macierzy 6 mikrofonów) — wtedy ciężar przechodzi na B, a raport to odnotuje.
- Częste okluzje graczy → podmiany ID trackera; atrybucja nie może polegać wyłącznie na ID toru (kolor stroju + naprzemienność uderzeń).
- Ceny API mogą się zmienić między spikiem a S-02 — raport zapisuje ceny z dnia pomiaru.
- Wynik na jednym nagraniu może nie generalizować (inne oświetlenie/stroje) — świadomie akceptowane; weryfikacja wyrywkowa to S-03.

## Success Criteria (Summary)

- Werdykt: nazwane podejście z zmierzonym błędem < 10% i kosztem ≤ 2 zł/mecz — albo świadoma decyzja użytkownika na bazie raportu częściowego.
- Benchmark zamrożony i udokumentowany jako narzędzie odbioru S-02.
- Łączny koszt eksperymentów ≤ 50 zł, wszystkie liczby raportu odtwarzalne skryptem.
