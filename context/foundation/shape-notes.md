---
project: "Squash Analyzer"
context_type: greenfield
created: 2026-08-05
updated: 2026-08-07
checkpoint:
  current_phase: 8
  phases_completed: [1, 2, 3, 4, 5, 6, 7]
  timeline_budget:
    mvp_weeks: 3
    hard_deadline: null
    after_hours_only: null
  gray_areas_resolved:
    - topic: "primary persona"
      decision: "jedna osoba w dwóch rolach — samotrenujący się zawodnik (gracz + własny trener)"
    - topic: "pain category"
      decision: "brakująca zdolność + paraliż decyzyjny"
    - topic: "insight vs istniejące narzędzia"
      decision: "cena/dostępność gotowych narzędzi + pełna kontrola nad metrykami (miejsce zagrania + miejsce odbicia)"
  frs_drafted: 8
  quality_check_status: accepted
---

# Shape Notes

## Seed idea

Aplikacja do analizy wideo meczów squasha: statystyki per zawodnik — liczba uderzeń, rodzaje uderzeń, miejsce zagrania, miejsce odbicia piłki.

## Vision & Problem Statement

Po meczu squasha zawodnik i trener nie mają żadnych danych o uderzeniach — liczbie, rodzajach, miejscach zagrania i miejscach odbicia piłki. Decyzje treningowe (nad czym pracować) opierają się wyłącznie na pamięci i wrażeniach z gry; obecnie ta informacja w ogóle nie istnieje. Rodzaj bólu: brakująca zdolność + paraliż decyzyjny.

Insight: gotowe narzędzia (Rally Vision ~99 USD/mecz, SquashTrack — waitlist, Core Analytics) są drogie lub niedostępne, a własne rozwiązanie daje pełną kontrolę nad metrykami, które faktycznie interesują użytkownika — w szczególności parą "miejsce zagrania → miejsce odbicia piłki" per uderzenie.

## User & Persona

Persona główna: **samotrenujący się zawodnik** — jedna osoba w dwóch rolach (gracz + własny trener). Gra mecze squasha, nagrywa je, a po meczu chce obiektywnych danych o własnej grze, żeby samodzielnie zdecydować, nad czym pracować na treningu. Moment sięgnięcia po produkt: po meczu, przy analizie nagrania.

## Access Control

Logowanie kontem (email lub OAuth). Płaski model użytkownika — bez ról: każdy zalogowany użytkownik widzi wyłącznie własne mecze i statystyki. Brak panelu admina, brak współdzielenia w MVP (rola trenera z dostępem do cudzych meczów — poza zakresem, potencjalnie v2). Niezalogowany użytkownik nie ma dostępu do żadnych danych meczowych.

## MVP flow

1. Użytkownik loguje się.
2. Wgrywa nagranie meczu — założenie: **stałe ujęcie zza tylnej szyby**, jedna kamera/telefon na statywie, cały kort w kadrze, stała pozycja przez cały mecz.
3. System automatycznie wykrywa zawodników i momenty uderzeń.
4. Użytkownik widzi per zawodnik: **liczbę uderzeń** i **mapę miejsc, z których padły zagrania**.

Decyzja zakresowa (scope-down z pełnej wersji): klasyfikacja rodzaju uderzenia i miejsce odbicia piłki — poza MVP, jawnie w Non-Goals (kandydaci do v2). Analiza automatyczna (bez ręcznego tagowania uderzeń).

## Success Criteria

### Primary
- Użytkownik wgrywa nagranie meczu (stałe ujęcie zza szyby) i bez ręcznej pracy otrzymuje per zawodnik: liczbę uderzeń oraz mapę miejsc zagrania.

### Secondary
- Porównanie między meczami: trend liczby uderzeń / pokrycia kortu między kolejnymi wgranymi meczami.
- Heatmapa pozycji całego meczu: ogólna mapa ciepła poruszania się zawodnika po korcie (oprócz miejsc zagrań).

### Guardrails
- Wiarygodność statystyk: licznik uderzeń blisko prawdy (błąd < 10%) — lepiej mniej metryk niż metryki zmyślone.
- Prywatność nagrań: wideo meczu (wizerunek użytkownika i przeciwnika) dostępne wyłącznie dla właściciela konta.
- Czas przetwarzania: analiza meczu kończy się w rozsądnym czasie (< 1h dla meczu) i nie blokuje korzystania z aplikacji.

## Functional Requirements

### Konto i dostęp
- FR-001: Użytkownik może założyć konto (rejestracja minimalna — bez weryfikacji email i odzyskiwania hasła w MVP). Priority: must-have
  > Socrates: Kontrargument: "rejestracja to zbędna praca, gdy jedynym użytkownikiem jesteś Ty; każdy dzień na auth to dzień nie na CV". Rezolucja: rejestracja zostaje, ale ścięta do absolutnego minimum.
- FR-002: Użytkownik może zalogować się przez OAuth (np. Google) — bez własnej obsługi haseł. Priority: must-have
  > Socrates: Kontrargument: "własne email+hasło = obsługa haseł, resetów i wycieków". Rezolucja: przyjęty — MVP loguje przez OAuth, zero własnego magazynu haseł.

### Mecze i nagrania
- FR-003: Użytkownik może wgrać nagranie meczu (pliki rzędu GB — upload musi być odporny na przerwanie). Priority: must-have
  > Socrates: Kontrargument: "upload przeglądarką przy plikach GB bywa zawodny; przerwany transfer frustruje". Rezolucja: uznany za realny koszt — wymaganie zapisuje niezawodność uploadu jako cechę; mechanizm (wznawianie itp.) to decyzja downstream.
- FR-004: Podczas wgrywania nagrania użytkownik podaje metadane meczu: imiona i nazwiska graczy oraz wynik; datę z godziną i czas gry system proponuje automatycznie (z metadanych pliku / długości wideo), z możliwością korekty. Priority: must-have
  > Socrates: Kontrargument: "część danych da się wyliczyć — ręczne wpisywanie dubluje to, co system i tak wie". Rezolucja: przyjęty — ręcznie tylko to, czego system nie zna (gracze, wynik); resztę proponuje automatycznie.
- FR-005: Użytkownik może zobaczyć listę swoich meczów wraz ze statusem przetwarzania każdego z nich (w trakcie analizy / gotowy / błąd). Priority: must-have
  > Socrates: Kontrargument: "analiza trwa do 1h — lista bez statusu myli, użytkownik nie wie, czemu nie ma statystyk". Rezolucja: przyjęty — status przetwarzania wchodzi do wymagania.

### Statystyki
- FR-006: Użytkownik może przejść z listy do konkretnego meczu i zobaczyć szczegóły — statystyki per zawodnik (liczba uderzeń, mapa miejsc zagrań). Priority: must-have
  > Socrates: Kontrargument: "liczby bez możliwości weryfikacji nie budują zaufania" (guardrail: wiarygodność). Rezolucja: przyjęty — dodano FR-008 (wyrywkowa weryfikacja wykrytych uderzeń z wideo).
- FR-007: Użytkownik może zaznaczyć na liście dwa mecze i zobaczyć ich porównanie. Priority: nice-to-have
  > Socrates: Kontrargument: "mecze różnią się przeciwnikiem i długością — porównanie 1:1 bez normalizacji może mylić". Rezolucja: przyjęty — porównanie musi normalizować (np. na gema/minutę); szczegół normalizacji do rozstrzygnięcia downstream.
- FR-008: Użytkownik może podejrzeć wykryte uderzenia na osi czasu wideo, aby wyrywkowo zweryfikować statystyki z nagraniem. Priority: must-have
  > Socrates: FR dodany jako rezolucja wyzwania FR-006 — bez możliwości sprawdzenia wykryć z wideo licznik uderzeń nie zbuduje zaufania.

## User Stories

### US-01: Użytkownik analizuje wgrany mecz

- **Given** zalogowany użytkownik z nagraniem meczu (stałe ujęcie zza szyby, cały kort w kadrze)
- **When** wgrywa nagranie, podaje graczy i wynik, i czeka na zakończenie automatycznej analizy
- **Then** widzi per zawodnik: liczbę uderzeń i mapę miejsc, z których padły zagrania

#### Acceptance Criteria
- Licznik uderzeń: błąd < 10% względem ręcznego zliczenia (guardrail wiarygodności).
- Na liście meczów widoczny status przetwarzania (w trakcie / gotowy / błąd); analiza kończy się < 1h.
- Mapa zagrań prezentowana na schemacie kortu, osobno dla każdego gracza.
- Wykryte uderzenia można obejrzeć na osi czasu wideo (FR-008).

## Business Logic

Na podstawie nagrania meczu system samodzielnie wykrywa każde uderzenie, przypisuje je do właściwego zawodnika i wyznacza miejsce na korcie, z którego padło zagranie — bez ręcznego tagowania.

Reguła konsumuje: nagranie meczu (stałe ujęcie zza tylnej szyby, cały kort w kadrze) oraz podane przez użytkownika imiona graczy i wynik. Jej wyjściem są statystyki per zawodnik: liczba uderzeń oraz mapa miejsc zagrania na schemacie kortu. Użytkownik spotyka regułę w widoku szczegółów meczu — po zakończeniu automatycznej analizy wgranego nagrania (status widoczny na liście meczów), z możliwością wyrywkowej weryfikacji wykryć na osi czasu wideo.

## Non-Functional Requirements

- Wiarygodność: liczba uderzeń per zawodnik z błędem < 10% względem ręcznego zliczenia.
- Czas analizy: statystyki meczu dostępne < 1h od wgrania; przetwarzanie nie blokuje korzystania z aplikacji.
- Prywatność: nagranie i statystyki widoczne wyłącznie dla właściciela konta; żadne dane meczowe nie są dostępne bez zalogowania.
- Koszt analizy: analiza jednego meczu mieści się w ustalonym pułapie kosztowym (rzędu pojedynczych złotych; dokładny pułap do potwierdzenia przy wyborze stacku).
- Dostępność: aplikacja użyteczna w aktualnych wersjach popularnych przeglądarek desktop i mobile (przeglądanie statystyk na telefonie).
- Trwałość danych: wgrane mecze i statystyki przechowywane bezterminowo, do ręcznego usunięcia przez użytkownika.

## Forward: tech-stack

- Użytkownik wskazał preferencję realizacji analizy wideo przez LLM/VLM ("aplikacja za pomocą LLM-a analizuje wgrane wideo"). To decyzja implementacyjna do zważenia na etapie wyboru stacku (LLM/VLM vs klasyczny pipeline CV vs hybryda) — m.in. względem NFR kosztu analizy i guardraila wiarygodności (<10% błędu licznika uderzeń).

## Product framing

- Rodzaj produktu: aplikacja webowa (upload przez przeglądarkę, statystyki dostępne też na telefonie) → `product_type: web-app`
- Skala: tylko ja / kilka osób → `target_scale.users: small`
  - Insight (Sokrates, skala 100×): przy setkach graczy koszt analizy per mecz stałby się krytyczny — wzmacnia NFR pułapu kosztowego już na etapie wyboru podejścia do analizy.
- Timeline: `mvp_weeks: 3`, `hard_deadline: null`, `after_hours_only: true`

## Non-Goals

- Klasyfikacja rodzaju uderzenia (drive, drop, boast…) — świadomie wycięta z MVP przy scope-down; kandydat do v2. Zapisana jako non-goal, żeby nie wróciła tylnymi drzwiami.
- Rola trenera i współdzielenie meczów — żadnego dostępu do cudzych meczów, zapraszania, zespołów; MVP jest jednoosobowe (płaski model użytkownika).
- Analiza na żywo przy korcie — wyłącznie analiza po meczu z wgranego nagrania; żadnego real-time trackingu.

Uwaga zakresowa: miejsce odbicia piłki jest poza MVP (decyzja scope-down z Fazy 3), ale użytkownik świadomie NIE zapisał go jako twardego non-goal — to najbliższy kandydat do v2.
