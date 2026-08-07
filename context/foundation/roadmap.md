---
project: "Squash Analyzer"
version: 2
status: draft
created: 2026-08-07
updated: 2026-08-07
prd_version: 2
main_goal: market-feedback
top_blocker: skills
---

# Roadmap: Squash Analyzer

> Derived from `context/foundation/prd.md` (v2) + auto-researched codebase baseline.
> Edit-in-place; archive when superseded.
> Slices below are listed in dependency order. The "At a glance" table is the index.

## Vision recap

Po meczu squasha zawodnik nie ma żadnych danych o własnych uderzeniach — decyzje treningowe opierają się na pamięci i wrażeniach. Squash Analyzer pozwala samotrenującemu się zawodnikowi wgrać nagranie meczu (stałe ujęcie zza szyby) i bez ręcznej pracy dostać per zawodnik: liczbę uderzeń i mapę miejsc zagrania. Całość wisi na jednym najbardziej ryzykownym założeniu — czyli na tym jednym niepotwierdzonym przekonaniu, którego upadek unieważnia resztę planu: że automatyczna analiza wideo policzy uderzenia z błędem < 10% i zmieści się w pułapie kosztowym rzędu pojedynczych złotych za mecz.

## North star

**S-02: Użytkownik po zakończonej automatycznej analizie widzi per zawodnik liczbę uderzeń i mapę miejsc zagrań** — to jest walidacyjny kamień milowy: dopóki analiza nie działa wiarygodnie i tanio, żadna inna część produktu nie ma znaczenia (cel: weryfikacja największego ryzyka).

> „Gwiazda przewodnia" (north star) oznacza tu: najmniejszy plaster end-to-end, którego dowiezienie udowadnia główną hipotezę produktu — umieszczony tak wcześnie, jak pozwalają jego wymagania wstępne, bo wszystko inne ma sens tylko, jeśli on zadziała.

## At a glance

| ID   | Change ID                      | Outcome (user can …)                                                     | Prerequisites    | PRD refs                         | Status   |
| ---- | ------------------------------ | ------------------------------------------------------------------------ | ---------------- | -------------------------------- | -------- |
| F-01 | analysis-feasibility-spike     | (foundation) podejście do analizy zwalidowane na nagraniu referencyjnym  | —                | NFR wiarygodność, NFR koszt      | ready    |
| F-02 | async-processing-skeleton      | (foundation) zadanie poza edge uruchamialne, statusy przejść rejestrowane | —                | NFR czas analizy, FR-005         | ready    |
| F-03 | deploy-on-merge                | (foundation) auto-deploy po merge; aplikacja dostępna z realnych urządzeń | —                | NFR dostępność                   | ready    |
| S-01 | match-upload-and-list          | użytkownik może wgrać mecz z metadanymi i widzieć go na liście ze statusem | —                | FR-003, FR-004, FR-005, US-01    | ready    |
| S-02 | first-automated-match-analysis | użytkownik widzi per zawodnik liczbę uderzeń i mapę zagrań po analizie   | F-01, F-02, S-01 | FR-006, US-01, NFR wiarygodność  | proposed |
| S-03 | hit-timeline-verification      | użytkownik może podejrzeć wykryte uderzenia na osi czasu wideo           | S-02             | FR-008, US-01                    | proposed |
| S-04 | external-provider-signin       | użytkownik może założyć konto i zalogować się zewnętrznym dostawcą       | —                | FR-001, FR-002                   | ready    |
| S-05 | match-comparison               | użytkownik może zaznaczyć dwa mecze i zobaczyć znormalizowane porównanie | S-02             | FR-007                           | blocked  |
| S-06 | position-heatmap               | użytkownik widzi heatmapę poruszania się zawodnika po korcie (cały mecz) | S-02             | FR-009                           | proposed |

## Streams

Navigation aid — groups items that share a Prerequisites chain. Canonical ordering still lives in the dependency graph below; this table is the proposed reading order across parallel tracks.

| Stream | Theme                  | Chain                              | Note                                                                     |
| ------ | ---------------------- | ---------------------------------- | ------------------------------------------------------------------------ |
| A      | Rdzeń analizy (ryzyko) | `F-01` → `S-02` → `S-03` / `S-05` / `S-06` | Ścieżka największego ryzyka — priorytet przy celu weryfikacji ryzyka. |
| B      | Dopływ meczów          | `S-01`                             | Dołącza do Streamu A na `S-02` (dostarcza nagranie i rekord meczu).      |
| C      | Przetwarzanie w tle    | `F-02`                             | Dołącza do Streamu A na `S-02` (mechanizm zadań poza edge).              |
| D      | Wdrożenie              | `F-03`                             | Samodzielny — otwiera weryfikację NFR dostępności na realnych urządzeniach. |
| E      | Konto                  | `S-04`                             | Samodzielny — wymiana auth email+hasło na zewnętrznego dostawcę.         |

## Baseline

What's already in place in the codebase as of `2026-08-07` (auto-researched + user-confirmed).
Foundations below assume these are present and do NOT re-scaffold them.

- **Frontend:** present — Astro 6 + React 19 islands + Tailwind 4 + shadcn/ui; routing i hydratacja działają (`astro.config.mjs`, `src/pages/`).
- **Backend / API:** present — SSR (`output: "server"`) + adapter Cloudflare; działające endpointy auth (`src/pages/api/auth/`), middleware z guardem tras (`src/middleware.ts`).
- **Data:** partial — Supabase CLI + `supabase/config.toml` są, ale zero migracji, zero seed, brak typów DB i dostępu do danych w `src/`; storage włączony w configu, nieużywany.
- **Auth:** partial — Supabase Auth wpięte end-to-end, ale wyłącznie email+hasło (`signInWithPassword`); żaden zewnętrzny dostawca nie jest włączony (wszystkie `[auth.external.*]` = false), a FR-002 wymaga logowania zewnętrznym dostawcą.
- **Deploy / infra:** partial — `wrangler.jsonc` + CI (lint+build w `.github/workflows/ci.yml`) są, ale brak kroku deploy; mechanizm zadań w tle (kolejki/workery/cron): brak.
- **Observability:** partial — tylko platformowe Workers Logs (`wrangler.jsonc`); zero instrumentacji aplikacyjnej. Świadomie zostaje prosto (cel: weryfikacja ryzyka, nie jakość operacyjna).

## Foundations

### F-01: Spike wykonalności analizy wideo

- **Outcome:** (foundation) podejście do automatycznej analizy (LLM/VLM vs klasyczne CV vs hybryda) zwalidowane na referencyjnym nagraniu meczu z ręcznie zliczonymi uderzeniami (ground truth przygotowany w ramach spike'a): zmierzony błąd licznika względem progu < 10% i zmierzony koszt analizy względem pułapu rzędu pojedynczych złotych — łącznie z kosztem ciągłego śledzenia pozycji zawodników (wymaganym przez FR-009), nie tylko detekcji uderzeń.
- **Change ID:** analysis-feasibility-spike
- **PRD refs:** NFR wiarygodność (< 10%), NFR koszt analizy, Business Logic, FR-009 (śledzenie pozycji), Open Question #1
- **Unlocks:** S-02 (wybór podejścia do analizy), S-06 (wykonalność kosztowa ciągłego śledzenia pozycji); redukuje Open Roadmap Question #1 (pułap kosztowy); ustanawia ścieżkę weryfikacji guardraila wiarygodności (benchmark ground-truth używany potem przy odbiorze S-02)
- **Prerequisites:** —
- **Parallel with:** F-02, F-03, S-01, S-04
- **Blockers:** —
- **Unknowns:**
  - Dokładny pułap kosztowy per mecz (PRD mówi „rzędu pojedynczych złotych") — Owner: użytkownik. Block: no (spike mierzy realny koszt i dostarcza danych do decyzji).
- **Risk:** największe ryzyko produktu i nieznana warstwa (blocker: umiejętności) — dlatego pierwszy; jeśli żadne podejście nie zmieści się w progach wiarygodności i kosztu, roadmapa wymaga rewizji zanim powstanie reszta.
- **Status:** ready

### F-02: Szkielet przetwarzania poza edge

- **Outcome:** (foundation) minimalny mechanizm zadań w tle: zadanie da się uruchomić poza runtime'em edge (który nie udźwignie ~1h analizy), a jego przejścia statusów (w trakcie / gotowe / błąd) są rejestrowane i odczytywalne — zweryfikowane na zadaniu-atrapie, bez logiki analizy.
- **Change ID:** async-processing-skeleton
- **PRD refs:** NFR czas analizy (< 1h, nieblokujące), FR-005 (statusy przetwarzania)
- **Unlocks:** S-02 (analiza jako zadanie asynchroniczne); ścieżka weryfikacji statusów z FR-005
- **Prerequisites:** —
- **Parallel with:** F-01, F-03, S-01, S-04
- **Blockers:** —
- **Unknowns:** —
- **Risk:** baseline zgłasza całkowity brak tej warstwy, a tech-stack jawnie ją flaguje; minimalny kontrakt (uruchom + status), nie kompletna infrastruktura — pełny pipeline wchodzi dopiero w S-02.
- **Status:** ready

### F-03: Auto-deploy po merge

- **Outcome:** (foundation) istniejące CI uzupełnione o krok deploy — po merge aplikacja jest dostępna pod publicznym adresem z realnych urządzeń.
- **Change ID:** deploy-on-merge
- **PRD refs:** NFR dostępność (statystyki na telefonie)
- **Unlocks:** ścieżka weryfikacji NFR dostępności dla S-02 (przeglądanie statystyk na telefonie) i realnego użycia S-01 (upload nagrania po meczu, nie tylko lokalnie)
- **Prerequisites:** —
- **Parallel with:** F-01, F-02, S-01, S-04
- **Blockers:** —
- **Unknowns:** —
- **Risk:** mały i niezależny; odkładanie sprawia, że plastry weryfikuje się tylko lokalnie, a NFR dostępności pozostaje niesprawdzalny.
- **Status:** ready

## Slices

### S-01: Wgranie meczu i lista ze statusem

- **Outcome:** użytkownik może wgrać nagranie meczu (pliki rzędu GB, upload odporny na przerwanie), podać graczy i wynik (data/czas gry zaproponowane automatycznie, z korektą) i zobaczyć mecz na swojej liście ze statusem przetwarzania.
- **Change ID:** match-upload-and-list
- **PRD refs:** FR-003, FR-004, FR-005, US-01, NFR prywatność, NFR trwałość danych
- **Prerequisites:** —
- **Parallel with:** F-01, F-02, F-03, S-04
- **Blockers:** —
- **Unknowns:** —
- **Risk:** pierwszy plaster dotykający danych — wprowadza model meczu i reguły dostępu „tylko właściciel" (NFR prywatności) przy okazji pierwszej realnej potrzeby; niezawodność uploadu GB to główna trudność techniczna plastra.
- **Status:** ready

### S-02: Pierwsza automatyczna analiza meczu

- **Outcome:** użytkownik po zakończeniu automatycznej analizy wgranego meczu widzi w szczegółach meczu, per zawodnik: liczbę uderzeń i mapę miejsc zagrań na schemacie kortu.
- **Change ID:** first-automated-match-analysis
- **PRD refs:** FR-006, US-01, Business Logic, NFR wiarygodność, NFR czas analizy, NFR koszt analizy
- **Prerequisites:** F-01 (wybrane i zwalidowane podejście), F-02 (mechanizm zadań w tle), S-01 (wgrany mecz z metadanymi)
- **Parallel with:** F-03, S-04
- **Blockers:** —
- **Unknowns:**
  - Czy podejście zwalidowane w F-01 na nagraniu referencyjnym utrzyma błąd < 10% na kolejnych meczach (inne oświetlenie, stroje, kort)? — Owner: użytkownik. Block: no (weryfikacja wyrywkowa wchodzi w S-03; odbiór S-02 używa benchmarku z F-01).
- **Risk:** gwiazda przewodnia — umieszczona najwcześniej, jak pozwalają wymagania wstępne; największy plaster roadmapy, ale ryzyko algorytmiczne zdjęte przez F-01, a infrastrukturalne przez F-02.
- **Status:** proposed

### S-03: Weryfikacja uderzeń na osi czasu wideo

- **Outcome:** użytkownik może podejrzeć wykryte uderzenia na osi czasu wideo i wyrywkowo porównać je z nagraniem — statystyki da się sprawdzić, nie tylko przyjąć na wiarę.
- **Change ID:** hit-timeline-verification
- **PRD refs:** FR-008, US-01, NFR wiarygodność
- **Prerequisites:** S-02
- **Parallel with:** S-04, S-05, S-06
- **Blockers:** —
- **Unknowns:** —
- **Risk:** domyka guardrail wiarygodności (FR-008 powstał właśnie po to); sekwencjonowany zaraz po S-02, bo bez niego licznik uderzeń nie zbuduje zaufania.
- **Status:** proposed

### S-04: Logowanie zewnętrznym dostawcą

- **Outcome:** użytkownik może założyć konto i zalogować się kontem zewnętrznego dostawcy tożsamości — bez własnej obsługi haseł (rejestracja minimalna: bez weryfikacji email i odzyskiwania hasła).
- **Change ID:** external-provider-signin
- **PRD refs:** FR-001, FR-002, Access Control
- **Prerequisites:** —
- **Parallel with:** F-01, F-02, F-03, S-01, S-02, S-03, S-05, S-06
- **Blockers:** —
- **Unknowns:** —
- **Risk:** baseline ma działające auth email+hasło, co jest sprzeczne z FR-002 — plaster wymienia mechanizm na zewnętrznego dostawcę; niezależny od ścieżki ryzyka, więc może iść równolegle w dowolnym momencie, ale przed realnym użyciem produktu (zero własnego magazynu haseł).
- **Status:** ready

### S-05: Porównanie dwóch meczów

- **Outcome:** użytkownik może zaznaczyć na liście dwa mecze i zobaczyć ich znormalizowane porównanie (trend liczby uderzeń / pokrycia kortu).
- **Change ID:** match-comparison
- **PRD refs:** FR-007 (nice-to-have), Success Criteria: Secondary
- **Prerequisites:** S-02 (statystyki istnieją dla ≥ 2 meczów)
- **Parallel with:** S-03, S-04, S-06
- **Blockers:** —
- **Unknowns:**
  - Sposób normalizacji porównania (na gema / na minutę) — mecze różnią się długością i przeciwnikiem — Owner: użytkownik. Block: yes.
- **Risk:** jedyny plaster nice-to-have; porównanie 1:1 bez normalizacji mogłoby mylić, więc nie wchodzi do planowania przed rozstrzygnięciem sposobu normalizacji.
- **Status:** blocked

### S-06: Heatmapa pozycji zawodnika

- **Outcome:** użytkownik widzi w szczegółach meczu heatmapę poruszania się zawodnika po korcie przez cały mecz, osobno dla każdego gracza — obok mapy miejsc zagrań.
- **Change ID:** position-heatmap
- **PRD refs:** FR-009, Success Criteria: Secondary, NFR koszt analizy
- **Prerequisites:** S-02 (pipeline analizy istnieje; heatmapa rozszerza go o ciągłe śledzenie pozycji)
- **Parallel with:** S-03, S-04, S-05
- **Blockers:** —
- **Unknowns:**
  - Czy ciągłe śledzenie pozycji mieści się w pułapie kosztowym przy podejściu wybranym w F-01? — Owner: użytkownik. Block: no (F-01 mierzy to w ramach spike'a; wynik warunkuje odbiór, nie planowanie).
- **Risk:** jedyny plaster, którego koszt rośnie z długością meczu niezależnie od liczby uderzeń — jeśli pomiar z F-01 pokaże przekroczenie pułapu, decyzja o heatmapie wraca do użytkownika (degradacja do próbkowania pozycji albo powrót do v2).
- **Status:** proposed

## Backlog Handoff

| Roadmap ID | Change ID                      | Suggested issue title                                        | Ready for `/10x-plan` | Notes                              |
| ---------- | ------------------------------ | ------------------------------------------------------------ | --------------------- | ---------------------------------- |
| F-01       | analysis-feasibility-spike     | Spike: walidacja podejścia do analizy wideo (błąd i koszt)   | yes                   | Run `/10x-plan analysis-feasibility-spike` |
| F-02       | async-processing-skeleton      | Szkielet zadań w tle poza edge (statusy przejść)             | yes                   | Run `/10x-plan async-processing-skeleton` |
| F-03       | deploy-on-merge                | Krok deploy w CI: auto-deploy po merge                       | yes                   | Run `/10x-plan deploy-on-merge`    |
| S-01       | match-upload-and-list          | Upload meczu (GB, odporny) + lista meczów ze statusem        | yes                   | Run `/10x-plan match-upload-and-list` |
| S-02       | first-automated-match-analysis | Automatyczna analiza meczu: liczba uderzeń + mapa zagrań     | no                    | Czeka na F-01, F-02, S-01          |
| S-03       | hit-timeline-verification      | Wykryte uderzenia na osi czasu wideo                         | no                    | Czeka na S-02                      |
| S-04       | external-provider-signin       | Logowanie zewnętrznym dostawcą tożsamości                    | yes                   | Run `/10x-plan external-provider-signin` |
| S-05       | match-comparison               | Znormalizowane porównanie dwóch meczów                       | no                    | Zablokowany: sposób normalizacji   |
| S-06       | position-heatmap               | Heatmapa pozycji zawodnika (cały mecz, per gracz)            | no                    | Czeka na S-02                      |

## Open Roadmap Questions

1. **Dokładny pułap kosztowy analizy jednego meczu** (NFR kosztu mówi „rzędu pojedynczych złotych") — Owner: użytkownik. Block: S-02 (wybór podejścia musi się w nim mieścić; F-01 dostarcza pomiar realnego kosztu jako podstawę decyzji).
2. **Sposób normalizacji porównania dwóch meczów (FR-007)** — normalizacja (na gema / na minutę) do zaprojektowania, gdy FR-007 wejdzie do realizacji — Owner: użytkownik. Block: S-05.

> Rozstrzygnięte 2026-08-07: dawne pytanie #3 (heatmapa pozycji bez pokrywającego FR) — decyzja: wchodzi do MVP. PRD v2 dostał FR-009 (must-have), roadmapa plaster S-06; walidacja kosztowa śledzenia pozycji dopisana do zakresu F-01.

## Parked

- **Klasyfikacja rodzaju uderzenia (drive, drop, boast…)** — Why parked: PRD §Non-Goals, świadomy scope-down; kandydat do v2.
- **Rola trenera i współdzielenie meczów** — Why parked: PRD §Non-Goals; MVP jest jednoosobowe, płaski model użytkownika.
- **Analiza na żywo przy korcie** — Why parked: PRD §Non-Goals; wyłącznie analiza po meczu z nagrania.
- **Obsługa dowolnych ujęć kamery** — Why parked: PRD §Non-Goals; MVP zakłada stałe ujęcie zza tylnej szyby.
- **Miejsce odbicia piłki** — Why parked: uwaga zakresowa w PRD — poza MVP, ale świadomie NIE twardy non-goal; najbliższy kandydat do v2.

## Done

(Empty on first generation. `/10x-archive` appends an entry here — and flips that item's `Status` to `done` — when a change whose `Change ID` matches the item is archived. Do NOT pre-populate.)
