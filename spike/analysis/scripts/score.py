"""Ocena pliku kandydata względem ground truth benchmarku.

Użycie (z katalogu spike/analysis):
    uv run python scripts/score.py out/candidate-A.json
    uv run python scripts/score.py out/candidate-A.json --gt benchmark/ground_truth.json --tol 1.0

Metryka progu (PRD): błąd % liczby uderzeń per zawodnik, łącznie ze wszystkich segmentów, < 10%.
Diagnostyka: dopasowanie zdarzeń w oknie ±tol s — precyzja i pokrycie, bez atrybucji
(sama detekcja momentu) oraz z atrybucją (zgodny gracz). Chroni przed "dobrą sumą"
z kompensujących się błędów.

Schemat wejścia (ground truth i kandydaci):
    {"<segment_id>": {"hits": [{"t": <sekundy od startu segmentu>, "player": "A" | "B"}]}}
Klucze najwyższego poziomu zaczynające się od "_" (np. "_meta") są ignorowane.

Kod wyjścia: 0 — raport wydrukowany (niezależnie od werdyktu); 2 — błędne wejście.
Wynik zapisywany deterministycznie do out/score-<nazwa pliku kandydata>.json.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAYERS = ("A", "B")
THRESHOLD_PCT = 10.0
EPS = 1e-9

Hits = list[tuple[float, str]]


class SchemaError(ValueError):
    pass


def load_hits(path: Path) -> dict[str, Hits]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SchemaError(f"{path}: nie można wczytać JSON ({exc})") from exc
    if not isinstance(data, dict):
        raise SchemaError(f"{path}: najwyższy poziom musi być obiektem {{segment_id: ...}}")

    segments: dict[str, Hits] = {}
    for seg_id, seg in data.items():
        if seg_id.startswith("_"):
            continue
        if not isinstance(seg, dict) or not isinstance(seg.get("hits"), list):
            raise SchemaError(f'{path}: segment "{seg_id}" musi mieć postać {{"hits": [...]}}')
        hits: Hits = []
        for i, hit in enumerate(seg["hits"]):
            where = f'{path}: segment "{seg_id}", hits[{i}]'
            if not isinstance(hit, dict):
                raise SchemaError(f"{where}: oczekiwano obiektu {{t, player}}")
            t, player = hit.get("t"), hit.get("player")
            if isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(t) or t < 0:
                raise SchemaError(f"{where}: t musi być nieujemną liczbą sekund, jest {t!r}")
            if player not in PLAYERS:
                raise SchemaError(f'{where}: player musi być "A" lub "B", jest {player!r}')
            hits.append((float(t), player))
        segments[seg_id] = sorted(hits)
    return segments


def count_error_pct(gt: int, cand: int) -> float | None:
    """Błąd względny liczby uderzeń; None, gdy nieokreślony (0 w ground truth, >0 u kandydata)."""
    if gt == 0:
        return 0.0 if cand == 0 else None
    return abs(cand - gt) / gt * 100.0


def match_count(gt_times: list[float], cand_times: list[float], tol: float) -> int:
    """Maksymalne dopasowanie 1:1 zdarzeń w oknie ±tol (obie listy posortowane).

    Dwa wskaźniki są optymalne w 1D: zdarzenie za wcześnie względem bieżącego partnera
    nie dopasuje się już do żadnego późniejszego, a łączenie najwcześniejszej pasującej
    pary nigdy nie pogarsza wyniku.
    """
    i = j = matched = 0
    while i < len(gt_times) and j < len(cand_times):
        delta = cand_times[j] - gt_times[i]
        if abs(delta) <= tol + EPS:
            matched += 1
            i += 1
            j += 1
        elif delta < 0:
            j += 1
        else:
            i += 1
    return matched


def ratio(num: int, den: int) -> float | None:
    return num / den if den else None


def match_stats(gt: Hits, cand: Hits, tol: float) -> dict[str, dict]:
    detection = match_count([t for t, _ in gt], [t for t, _ in cand], tol)
    attributed = sum(
        match_count([t for t, p in gt if p == player], [t for t, p in cand if p == player], tol)
        for player in PLAYERS
    )
    return {
        name: {
            "matched": m,
            "gt": len(gt),
            "cand": len(cand),
            "precision": ratio(m, len(cand)),
            "recall": ratio(m, len(gt)),
        }
        for name, m in (("detection", detection), ("attributed", attributed))
    }


def count_stats(gt: Hits, cand: Hits) -> dict[str, dict]:
    stats = {}
    for player in PLAYERS:
        n_gt = sum(1 for _, p in gt if p == player)
        n_cand = sum(1 for _, p in cand if p == player)
        stats[player] = {"gt": n_gt, "cand": n_cand, "error_pct": count_error_pct(n_gt, n_cand)}
    return stats


def merge_stats(parts: list[dict[str, dict]]) -> dict[str, dict]:
    merged = {}
    for name in ("detection", "attributed"):
        m = sum(p[name]["matched"] for p in parts)
        n_gt = sum(p[name]["gt"] for p in parts)
        n_cand = sum(p[name]["cand"] for p in parts)
        merged[name] = {
            "matched": m,
            "gt": n_gt,
            "cand": n_cand,
            "precision": ratio(m, n_cand),
            "recall": ratio(m, n_gt),
        }
    return merged


def score(gt: dict[str, Hits], cand: dict[str, Hits], tol: float) -> dict:
    missing = [seg_id for seg_id in gt if seg_id not in cand]
    if missing:
        raise SchemaError(f"kandydat nie zawiera segmentów z ground truth: {', '.join(missing)}")

    segments = {}
    for seg_id, gt_hits in gt.items():
        cand_hits = cand[seg_id]
        segments[seg_id] = {"counts": count_stats(gt_hits, cand_hits), **match_stats(gt_hits, cand_hits, tol)}

    all_gt = [h for hits in gt.values() for h in hits]
    all_cand = [cand[seg_id][k] for seg_id in gt for k in range(len(cand[seg_id]))]
    total = {"counts": count_stats(all_gt, all_cand), **merge_stats(list(segments.values()))}

    errors = [total["counts"][p]["error_pct"] for p in PLAYERS]
    max_error = None if not all_gt or any(e is None for e in errors) else max(errors)
    passed = max_error is not None and max_error < THRESHOLD_PCT
    return {
        "tolerance_s": tol,
        "threshold_pct": THRESHOLD_PCT,
        "segments": segments,
        "total": total,
        "max_player_error_pct": max_error,
        "pass": passed,
    }


def fmt_pct(value: float | None, scale: float = 1.0) -> str:
    return "n/d" if value is None else f"{value * scale:.1f}%"


def print_report(result: dict, candidate: str, gt_path: str) -> None:
    tol = result["tolerance_s"]
    rows = [*result["segments"].items(), ("ŁĄCZNIE", result["total"])]

    print(f"Kandydat:     {candidate}")
    print(f"Ground truth: {gt_path}\n")
    print("Liczba uderzeń per zawodnik (metryka progu)")
    print(f"{'segment':<10} {'gracz':<6} {'GT':>5} {'kand.':>6} {'błąd':>8}")
    for seg_id, stats in rows:
        for player in PLAYERS:
            c = stats["counts"][player]
            print(f"{seg_id:<10} {player:<6} {c['gt']:>5} {c['cand']:>6} {fmt_pct(c['error_pct']):>8}")

    print(f"\nDopasowanie zdarzeń ±{tol:g} s (diagnostyka)")
    print(f"{'segment':<10} {'detekcja P':>11} {'detekcja R':>11} {'z atryb. P':>11} {'z atryb. R':>11}")
    for seg_id, stats in rows:
        d, a = stats["detection"], stats["attributed"]
        print(
            f"{seg_id:<10} {fmt_pct(d['precision'], 100):>11} {fmt_pct(d['recall'], 100):>11}"
            f" {fmt_pct(a['precision'], 100):>11} {fmt_pct(a['recall'], 100):>11}"
        )

    print()
    if result["total"]["detection"]["gt"] == 0:
        print("UWAGA: ground truth jest pusty — uzupełnij benchmark/ground_truth.json (protokół w README).")
    verdict = "PASS" if result["pass"] else "FAIL"
    print(
        f"WERDYKT (błąd per zawodnik < {THRESHOLD_PCT:g}%): {verdict}"
        f" — maks. błąd {fmt_pct(result['max_player_error_pct'])}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Ocena kandydata względem ground truth benchmarku.")
    parser.add_argument("candidate", type=Path, help="plik JSON kandydata w schemacie benchmarku")
    parser.add_argument("--gt", type=Path, default=ROOT / "benchmark" / "ground_truth.json")
    parser.add_argument("--tol", type=float, default=1.0, help="okno dopasowania zdarzeń w sekundach")
    parser.add_argument("--out", type=Path, help="plik wyniku (domyślnie out/score-<kandydat>.json)")
    args = parser.parse_args()

    try:
        gt = load_hits(args.gt)
        cand = load_hits(args.candidate)
        extra = sorted(set(cand) - set(gt))
        if extra:
            print(f"UWAGA: pomijam segmenty spoza ground truth: {', '.join(extra)}", file=sys.stderr)
        result = score(gt, cand, args.tol)
    except SchemaError as exc:
        print(f"BŁĄD: {exc}", file=sys.stderr)
        return 2

    print_report(result, str(args.candidate), str(args.gt))

    out_path = args.out or ROOT / "out" / f"score-{args.candidate.stem}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"candidate": str(args.candidate), "ground_truth": str(args.gt), **result}
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nWynik zapisany: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
