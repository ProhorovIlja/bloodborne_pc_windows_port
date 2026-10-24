#!/usr/bin/env python3
# Adapted from ProhorovIlja/tekken6-native-online-source
# (feature/long-session-process-memory-trace); developer-side only.
"""Offline Bloodborne PC host-process memory trend analysis from collect_process_memory.ps1.

The analysis flags sustained process memory growth; it cannot prove a leak or
identify one object's owner. Separate observations by PID + process start
timestamp to avoid confusing a restarted game's memory with a long session.

    python tools/diagnostics/process_memory_report.py runs/bloodborne_process_memory.csv
    python tools/diagnostics/process_memory_report.py runs/bloodborne_process_memory.csv --json
    python tools/diagnostics/process_memory_report.py runs/bloodborne_process_memory.csv --fail-on-growth
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics

MiB = 1024 * 1024
MAX_BYTES = 16 * MiB
FIELDS = ("timestamp_utc", "pid", "process_start_utc", "private_bytes",
          "working_set_bytes", "virtual_bytes", "handles", "threads")


class BadSample(ValueError):
    pass


@dataclass(frozen=True)
class Sample:
    when: datetime
    pid: int
    started: datetime
    private: int
    working: int
    virtual: int
    handles: int
    threads: int


@dataclass(frozen=True)
class Phase:
    samples: int
    private_mib_median: float
    working_mib_median: float
    handles_median: float
    threads_median: float


@dataclass(frozen=True)
class ProcessTrend:
    pid: int
    start_utc: str
    samples: int
    observed_seconds: float
    early: Phase | None
    middle: Phase | None
    late: Phase | None
    private_growth_mib: float | None
    handle_growth: float | None
    suspicious_growth: bool
    reasons: list[str]
    notes: list[str]


@dataclass(frozen=True)
class Report:
    source: str
    total_samples: int
    process_lifetimes: int
    suspicious_growth: bool
    processes: list[ProcessTrend]
    cautions: list[str]


def parse_utc(value: str, *, row_number: int) -> datetime:
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise BadSample(f"row {row_number}: invalid timestamp") from exc
    if dt.tzinfo is None:
        raise BadSample(f"row {row_number}: timestamp has no UTC offset")
    return dt.astimezone(timezone.utc)


def load(path: Path) -> list[Sample]:
    if path.stat().st_size > MAX_BYTES:
        raise BadSample(f"{path.name}: CSV exceeds {MAX_BYTES // MiB} MiB safety limit")
    out: list[Sample] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or tuple(reader.fieldnames) != FIELDS:
            raise BadSample(f"{path.name}: missing or unexpected CSV columns")
        for row_no, row in enumerate(reader, 2):
            if None in row or any(v is None for v in row.values()):
                raise BadSample(f"{path.name}:{row_no}: wrong number of CSV columns")
            try:
                values = [int(row[k], 10) for k in FIELDS[1:2] + FIELDS[3:]]
            except ValueError as exc:
                raise BadSample(f"{path.name}:{row_no}: invalid numeric field") from exc
            pid, private, working, virtual, handles, threads = values
            if pid <= 0 or min(private, working, virtual, handles, threads) < 0:
                raise BadSample(f"{path.name}:{row_no}: impossible counter value")
            out.append(Sample(
                when=parse_utc(row["timestamp_utc"], row_number=row_no),
                pid=pid,
                started=parse_utc(row["process_start_utc"], row_number=row_no),
                private=private, working=working, virtual=virtual,
                handles=handles, threads=threads,
            ))
    if not out:
        raise BadSample(f"{path.name}: no process-memory samples were captured")
    return out


def phase(values: list[Sample]) -> Phase:
    return Phase(
        samples=len(values),
        private_mib_median=statistics.median(v.private for v in values) / MiB,
        working_mib_median=statistics.median(v.working for v in values) / MiB,
        handles_median=float(statistics.median(v.handles for v in values)),
        threads_median=float(statistics.median(v.threads for v in values)),
    )


def process_trend(
    samples: list[Sample], *,
    min_samples: int = 12,
    private_growth_mib: float = 64.0,
    private_growth_pct: float = 20.0,
    handle_growth_min: float = 50.0,
) -> ProcessTrend:
    rows = sorted(samples, key=lambda s: s.when)
    pid = rows[0].pid
    start = rows[0].started.isoformat()
    notes: list[str] = []
    reasons: list[str] = []
    early = mid = late = None
    private_diff = handle_diff = None
    seconds = max(0.0, (rows[-1].when - rows[0].when).total_seconds())
    if seconds < 120:
        notes.append("Less than two minutes of process lifetime observed; cannot assess match-to-match growth.")
    if len(rows) < min_samples:
        notes.append(f"Only {len(rows)} observations; need at least {min_samples}.")
    elif seconds < 120:
        notes.append("Too short for a trustworthy trend even with many samples.")
    else:
        size = len(rows) // 3
        early, mid, late = phase(rows[:size]), phase(rows[size:2 * size]), phase(rows[-size:])
        private_diff = late.private_mib_median - early.private_mib_median
        handle_diff = late.handles_median - early.handles_median
        # Require a persistent rising trajectory rather than one late spike.
        # Bytes still reserved by an allocator for reuse are NOT proof of a leak.
        enough_private = (
            private_diff >= private_growth_mib
            and early.private_mib_median > 0
            and 100 * private_diff / early.private_mib_median >= private_growth_pct
            and early.private_mib_median < mid.private_mib_median < late.private_mib_median
        )
        if enough_private:
            reasons.append(
                f"Median private bytes rose by {private_diff:.1f} MiB "
                f"({100 * private_diff / early.private_mib_median:.1f}%) across all three phases."
            )
        if (handle_diff >= handle_growth_min
                and early.handles_median < mid.handles_median < late.handles_median):
            reasons.append(
                f"Median open handles rose by {handle_diff:.0f} across all three phases."
            )
    return ProcessTrend(
        pid=pid, start_utc=start, samples=len(rows), observed_seconds=seconds,
        early=early, middle=mid, late=late,
        private_growth_mib=private_diff, handle_growth=handle_diff,
        suspicious_growth=bool(reasons), reasons=reasons, notes=notes,
    )


def analyze(
    path: Path, *,
    min_samples: int = 12,
    private_growth_mib: float = 64.0,
    private_growth_pct: float = 20.0,
) -> Report:
    data = load(path)
    grouped: dict[tuple[int, datetime], list[Sample]] = {}
    for s in data:
        if s.when < s.started:
            raise BadSample(f"{path.name}: sample predates process start (PID {s.pid})")
        grouped.setdefault((s.pid, s.started), []).append(s)
    processes = [
        process_trend(group, min_samples=min_samples,
                      private_growth_mib=private_growth_mib,
                      private_growth_pct=private_growth_pct)
        for _, group in sorted(grouped.items())
    ]
    return Report(
        source=str(path), total_samples=len(data), process_lifetimes=len(grouped),
        suspicious_growth=any(p.suspicious_growth for p in processes),
        processes=processes,
        cautions=[
            "Reserved memory/working-set growth is not proof of a leak; allocators and shader caches warm up.",
            "Virtual address space is not RAM consumption in this native PC port.",
            "Correlation with native game logs, GPU memory and long repeat-match reproduction is required.",
        ],
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("csv", type=Path)
    p.add_argument("--min-samples", type=int, default=12)
    p.add_argument("--private-growth-mib", type=float, default=64.0)
    p.add_argument("--private-growth-pct", type=float, default=20.0)
    p.add_argument("--fail-on-growth", action="store_true",
                   help="Exit 3 for sustained growth or insufficient samples")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    if args.min_samples < 3 or min(args.private_growth_mib, args.private_growth_pct) < 0:
        p.error("min-samples must be >=3 and growth thresholds must be nonnegative")
    try:
        result = analyze(args.csv, min_samples=args.min_samples,
                         private_growth_mib=args.private_growth_mib,
                         private_growth_pct=args.private_growth_pct)
    except (OSError, UnicodeError, BadSample) as exc:
        p.exit(2, f"Cannot inspect process memory: {exc}\n")
    if args.json:
        print(json.dumps(asdict(result), indent=2))
    else:
        print(f"BLOODBORNE PC LONG-SESSION MEMORY CHECK: {result.source}")
        print(f"{result.total_samples} samples across {result.process_lifetimes} process lifetimes")
        for row in result.processes:
            print(f"PID {row.pid}, start {row.start_utc}: {row.samples} samples, "
                  f"{row.observed_seconds:.0f} s, "
                  f"private growth {row.private_growth_mib}, handle growth {row.handle_growth}")
            for title, part in (("EARLY", row.early), ("MIDDLE", row.middle), ("LATE", row.late)):
                if part:
                    print(f"  {title}: private {part.private_mib_median:.1f} MiB, "
                          f"working {part.working_mib_median:.1f} MiB, "
                          f"handles {part.handles_median:.0f}, threads {part.threads_median:.0f}")
            for msg in row.reasons:
                print("  POSSIBLE SUSTAINED GROWTH:", msg)
            for msg in row.notes:
                print("  NOTE:", msg)
        for caution in result.cautions:
            print("CAUTION:", caution)
        print("POSSIBLE GROWTH" if result.suspicious_growth else "No sustained growth established")
    if args.fail_on_growth and (
        result.suspicious_growth
        or any(p.samples < args.min_samples or p.observed_seconds < 120 for p in result.processes)
    ):
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
