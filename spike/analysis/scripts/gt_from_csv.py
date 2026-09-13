"""Buduje benchmark/ground_truth.json z ręcznych notatek CSV (ułatwienie do zliczania).

Format CSV — jedna linia na uderzenie, `#` rozpoczyna komentarz (także na końcu wiersza):
    segment,czas,gracz
    early,0:07,A
    early,0:09.5,B
Czas: "M:SS" / "M:SS.s" albo sekundy od początku pliku media/seg-{id}.mp4.

Użycie (z katalogu spike/analysis):
    uv run python scripts/gt_from_csv.py benchmark/ground_truth.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from extract_segments import DEFAULT_MANIFEST, ManifestError, load_manifest, parse_time

ROOT = Path(__file__).resolve().parent.parent
PLAYERS = ("A", "B")
DUPLICATE_WINDOW_S = 0.3


def main() -> int:
    parser = argparse.ArgumentParser(description="CSV z notatkami → ground_truth.json")
    parser.add_argument("csv", type=Path)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out", type=Path, default=ROOT / "benchmark" / "ground_truth.json")
    args = parser.parse_args()

    try:
        _, _, segments = load_manifest(args.manifest)
    except ManifestError as exc:
        print(f"BŁĄD manifestu: {exc}", file=sys.stderr)
        return 2
    durations = {seg.id: seg.duration for seg in segments}
    hits: dict[str, list[dict]] = {seg.id: [] for seg in segments}

    errors = []
    with args.csv.open(encoding="utf-8", newline="") as fh:
        lines = (line.split("#", 1)[0] for line in fh)
        rows = csv.reader(line for line in lines if line.strip())
        for lineno, row in enumerate(rows, start=1):
            cells = [c.strip() for c in row]
            if cells == ["segment", "czas", "gracz"]:
                continue
            if len(cells) != 3:
                errors.append(f"wiersz {lineno}: oczekiwano 3 kolumn, jest {len(cells)}")
                continue
            seg_id, raw_time, player = cells
            player = player.upper()
            if seg_id not in hits:
                errors.append(f"wiersz {lineno}: nieznany segment {seg_id!r}")
                continue
            if player not in PLAYERS:
                errors.append(f"wiersz {lineno}: gracz musi być A lub B, jest {player!r}")
                continue
            try:
                t = parse_time(raw_time, f"wiersz {lineno}")
            except ManifestError as exc:
                errors.append(str(exc))
                continue
            if t > durations[seg_id] + 5:
                errors.append(f"wiersz {lineno}: czas {raw_time} poza długością segmentu {seg_id}")
                continue
            hits[seg_id].append({"t": round(t, 2), "player": player})

    if errors:
        print("BŁĘDY w CSV:\n  " + "\n  ".join(errors), file=sys.stderr)
        return 2

    for seg_id, seg_hits in hits.items():
        seg_hits.sort(key=lambda h: (h["t"], h["player"]))
        for prev, cur in zip(seg_hits, seg_hits[1:]):
            if cur["player"] == prev["player"] and cur["t"] - prev["t"] < DUPLICATE_WINDOW_S:
                print(f"UWAGA: {seg_id} {prev['t']} s i {cur['t']} s — możliwy duplikat ({cur['player']})")
        counts = {p: sum(1 for h in seg_hits if h["player"] == p) for p in PLAYERS}
        print(f"{seg_id}: A={counts['A']} B={counts['B']}")

    payload = {seg_id: {"hits": seg_hits} for seg_id, seg_hits in hits.items()}
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Zapisano: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
