"""Wycina segmenty benchmarku z nagrania źródłowego według benchmark/segments.yaml.

Użycie (z katalogu spike/analysis):
    uv run python scripts/extract_segments.py                  # źródło: media/<source> z manifestu
    uv run python scripts/extract_segments.py --source ~/Movies/mecz.mp4
    uv run python scripts/extract_segments.py --check          # tylko weryfikacja istniejących segmentów

Cięcie bez rekompresji (-c copy): segment zaczyna się na klatce kluczowej przy znaczniku
startu, więc jego długość może odbiegać od manifestu o odstęp między klatkami kluczowymi.
Ground truth liczymy na wyciętych plikach media/seg-{id}.mp4, dlatego czasy uderzeń są
spójne z tym, co dostają kandydaci.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "benchmark" / "segments.yaml"
SEGMENT_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
PLAYERS = ("A", "B")


class ManifestError(ValueError):
    pass


@dataclass(frozen=True)
class Segment:
    id: str
    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


def parse_time(value: object, where: str) -> float:
    """Akceptuje "HH:MM:SS", "MM:SS" (z opcjonalnymi ułamkami) albo liczbę sekund."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        seconds = float(value)
    elif isinstance(value, str) and re.fullmatch(r"\d+(:\d{1,2}){0,2}(\.\d+)?", value.strip()):
        seconds = 0.0
        for part in value.strip().split(":"):
            seconds = seconds * 60 + float(part)
    else:
        raise ManifestError(f'{where}: nieprawidłowy czas {value!r} (oczekiwano "HH:MM:SS")')
    if seconds < 0:
        raise ManifestError(f"{where}: czas nie może być ujemny")
    return seconds


def load_manifest(path: Path) -> tuple[str, dict[str, str], list[Segment]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ManifestError(f"{path}: manifest musi być mapą")

    source = data.get("source")
    if not isinstance(source, str) or not source.strip():
        raise ManifestError(f"{path}: brak pola source")

    players = data.get("players")
    if not isinstance(players, dict) or any(not isinstance(players.get(p), str) for p in PLAYERS):
        raise ManifestError(f"{path}: players musi zawierać opisy strojów dla A i B")

    raw_segments = data.get("segments")
    if not isinstance(raw_segments, list) or not raw_segments:
        raise ManifestError(f"{path}: segments musi być niepustą listą")

    segments: list[Segment] = []
    for i, raw in enumerate(raw_segments):
        where = f"{path}: segments[{i}]"
        if not isinstance(raw, dict):
            raise ManifestError(f"{where}: oczekiwano mapy {{id, start, end}}")
        seg_id = str(raw.get("id", ""))
        if not SEGMENT_ID.match(seg_id):
            raise ManifestError(f"{where}: id {seg_id!r} musi pasować do [a-z0-9-]+")
        if any(s.id == seg_id for s in segments):
            raise ManifestError(f"{where}: zduplikowane id {seg_id!r}")
        seg = Segment(seg_id, parse_time(raw.get("start"), f"{where}.start"), parse_time(raw.get("end"), f"{where}.end"))
        if seg.duration <= 0:
            raise ManifestError(f"{where}: end musi być po start")
        segments.append(seg)
    return source, players, segments


def todo_fields(source: str, players: dict[str, str]) -> list[str]:
    fields = ["source"] if source.startswith("TODO") else []
    fields += [f"players.{p}" for p in PLAYERS if players[p].startswith("TODO")]
    return fields


def probe(path: Path) -> tuple[float, set[str]]:
    """Zwraca (długość w sekundach, typy strumieni) pliku multimedialnego."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration:stream=codec_type",
            "-of", "default=noprint_wrappers=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    duration, streams = None, set()
    for line in result.stdout.splitlines():
        key, _, value = line.partition("=")
        if key == "duration":
            duration = float(value)
        elif key == "codec_type":
            streams.add(value)
    if duration is None:
        raise RuntimeError(f"ffprobe nie zwrócił długości dla {path}")
    return duration, streams


def segment_path(media_dir: Path, seg: Segment) -> Path:
    return media_dir / f"seg-{seg.id}.mp4"


def extract(source: Path, seg: Segment, out: Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y",
            "-ss", f"{seg.start:.3f}",
            "-i", str(source),
            "-t", f"{seg.duration:.3f}",
            "-map", "0:v:0", "-map", "0:a:0",
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            "-movflags", "+faststart",
            str(out),
        ],
        check=True,
    )


def check(segments: list[Segment], media_dir: Path, tol: float) -> bool:
    ok = True
    for seg in segments:
        path = segment_path(media_dir, seg)
        if not path.exists():
            print(f"  ✗ {path.name}: brak pliku")
            ok = False
            continue
        duration, streams = probe(path)
        problems = []
        if abs(duration - seg.duration) > tol:
            problems.append(f"długość {duration:.1f} s vs manifest {seg.duration:.1f} s (tolerancja ±{tol:g} s)")
        if not {"video", "audio"} <= streams:
            problems.append(f"strumienie {sorted(streams)} — wymagane video i audio")
        mark = "✗" if problems else "✓"
        print(f"  {mark} {path.name}: {duration:.1f} s" + (f" — {'; '.join(problems)}" if problems else ""))
        ok = ok and not problems
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Wycina segmenty benchmarku z nagrania źródłowego.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--source", type=Path, help="ścieżka nagrania (nadpisuje media/<source> i SPIKE_SOURCE)")
    parser.add_argument("--media-dir", type=Path, default=ROOT / "media")
    parser.add_argument("--force", action="store_true", help="nadpisz istniejące segmenty")
    parser.add_argument("--check", action="store_true", help="tylko zweryfikuj istniejące segmenty")
    parser.add_argument("--tol", type=float, default=2.0, help="tolerancja długości segmentu w sekundach")
    args = parser.parse_args()

    try:
        source_name, players, segments = load_manifest(args.manifest)
    except ManifestError as exc:
        print(f"BŁĄD manifestu: {exc}", file=sys.stderr)
        return 2

    if not args.check:
        todo = todo_fields(source_name, players)
        if todo and not args.source:
            print(f"BŁĄD: manifest ma nieuzupełnione pola: {', '.join(todo)}", file=sys.stderr)
            return 2
        if todo:
            print(f"UWAGA: manifest ma nieuzupełnione pola: {', '.join(todo)}", file=sys.stderr)

        env_source = os.environ.get("SPIKE_SOURCE")
        source = (args.source or (Path(env_source) if env_source else args.media_dir / source_name)).expanduser()
        if not source.exists():
            print(f"BŁĄD: nie znaleziono nagrania źródłowego: {source}", file=sys.stderr)
            return 2

        source_duration, streams = probe(source)
        if not {"video", "audio"} <= streams:
            print(f"BŁĄD: nagranie musi mieć obraz i dźwięk, ma: {sorted(streams)}", file=sys.stderr)
            return 2
        too_long = [s.id for s in segments if s.end > source_duration]
        if too_long:
            print(
                f"BŁĄD: segmenty {', '.join(too_long)} wychodzą poza nagranie ({source_duration:.0f} s)",
                file=sys.stderr,
            )
            return 2

        args.media_dir.mkdir(parents=True, exist_ok=True)
        for seg in segments:
            out = segment_path(args.media_dir, seg)
            if out.exists() and not args.force:
                print(f"  = {out.name}: istnieje, pomijam (--force, aby nadpisać)")
                continue
            print(f"  → {out.name}: {seg.start:.0f}–{seg.end:.0f} s")
            extract(source, seg, out)

    print("Weryfikacja segmentów względem manifestu:")
    return 0 if check(segments, args.media_dir, args.tol) else 1


if __name__ == "__main__":
    sys.exit(main())
