#!/usr/bin/env python3
"""Keep the README's counts honest by generating them.

The badges and the stats table drifted three times in a single week — 327+, then
563, while the real figure moved to 577 — because every number was hand-edited
and nothing checked it. Numbers that a human maintains are numbers that lie.

Usage:
    python scripts/readme-stats.py --check    # exit 1 if the README is stale
    python scripts/readme-stats.py --write    # rewrite the README in place

``--check`` runs in CI. Mount a router, forget the README, and the build says so.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"


def _endpoint_counts() -> tuple[int, int, int]:
    """(operations, distinct /api paths, mounted routers) from the real app.

    Imported rather than grepped: a decorator on a router that is never mounted
    is not an endpoint, and grep cannot tell the difference. That distinction is
    the whole reason ten route modules were once dead code.
    """
    sys.path.insert(0, str(ROOT / "backend"))
    from app.api.router import api_router  # noqa: PLC0415
    from app.main import app  # noqa: PLC0415

    operations = 0
    api_paths: set[str] = set()
    for route in app.routes:
        methods = getattr(route, "methods", None)
        path = getattr(route, "path", "")
        if not methods:
            continue
        real = {m for m in methods if m not in ("HEAD", "OPTIONS")}
        operations += len(real)
        if path.startswith("/api"):
            api_paths.add(path)

    routers = len({id(r) for r in api_router.routes})
    included = len(
        {
            getattr(r, "tags", None) and tuple(r.tags) or getattr(r, "path", "")
            for r in api_router.routes
        }
    )
    del included, routers
    # Count the include_router calls, which is what "routers mounted" means.
    router_count = len(
        re.findall(r"^\s*api_router\.include_router\(", (ROOT / "backend/app/api/router.py").read_text(encoding="utf-8"), re.M)
    )
    return operations, len(api_paths), router_count


def _source_files() -> int:
    roots = [ROOT / "backend/app", ROOT / "frontend/src", ROOT / "sdk"]
    suffixes = {".py", ".ts", ".tsx"}
    total = 0
    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.suffix in suffixes and "node_modules" not in path.parts:
                total += 1
    return total


def _frontend_pages() -> tuple[int, int]:
    """(dashboard views, total routes) — `page.tsx` files under the app router."""
    app_dir = ROOT / "frontend/src/app"
    pages = [p for p in app_dir.rglob("page.tsx") if "node_modules" not in p.parts]
    dashboard = [p for p in pages if "(dashboard)" in p.as_posix()]
    return len(dashboard), len(pages)


def _module_rows() -> int:
    """Rows in the README's own module table — the one figure it defines itself."""
    text = README.read_text(encoding="utf-8")
    table = re.search(r"## Complete Module Table(.*?)(?=\n## )", text, re.S)
    if not table:
        return 0
    # Data rows carry a backticked route prefix in their third cell. Counting on
    # the first cell would miss the "| -- |" rows, which are modules too — they
    # just have no number.
    row = r"^\|[^|\n]*\|[^|\n]*\|\s*`[^`]+`"
    return len(re.findall(row, table.group(1), re.M))


def compute() -> dict[str, int]:
    operations, api_paths, routers = _endpoint_counts()
    dashboard_pages, total_pages = _frontend_pages()
    return {
        "modules": _module_rows(),
        "routers": routers,
        "endpoints": operations,
        "api_paths": api_paths,
        "source_files": _source_files(),
        "dashboard_pages": dashboard_pages,
        "total_pages": total_pages,
    }


def render(text: str, stats: dict[str, int]) -> str:
    text = re.sub(
        r"(!\[Modules\]\(https://img\.shields\.io/badge/modules-)\d+",
        rf"\g<1>{stats['modules']}",
        text,
    )
    text = re.sub(
        r"(!\[Endpoints\]\(https://img\.shields\.io/badge/endpoints-)\d+",
        rf"\g<1>{stats['endpoints']}",
        text,
    )
    text = re.sub(
        r"(\| \*\*Modules\*\* \| )\d+( \| rows in the module table below \()\d+( routers are mounted)",
        rf"\g<1>{stats['modules']}\g<2>{stats['routers']}\g<3>",
        text,
    )
    text = re.sub(
        r"(\| \*\*Source Files\*\* \| )\d+",
        rf"\g<1>{stats['source_files']}",
        text,
    )
    text = re.sub(
        r"(\| \*\*API Endpoints\*\* \| )\d+(.*?across )\d+( distinct)",
        rf"\g<1>{stats['endpoints']}\g<2>{stats['api_paths']}\g<3>",
        text,
    )
    text = re.sub(
        r"(\| \*\*Frontend Pages\*\* \| )\d+( dashboard views \()\d+( routes)",
        rf"\g<1>{stats['dashboard_pages']}\g<2>{stats['total_pages']}\g<3>",
        text,
    )
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--write", action="store_true")
    args = parser.parse_args()

    stats = compute()
    current = README.read_text(encoding="utf-8")
    updated = render(current, stats)

    if args.write:
        if updated != current:
            README.write_text(updated, encoding="utf-8", newline="\n")
            print("README updated:")
        else:
            print("README already current:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        return 0

    if updated != current:
        print("README stats are stale. Measured:", file=sys.stderr)
        for key, value in stats.items():
            print(f"  {key}: {value}", file=sys.stderr)
        print(
            "\nRun `python scripts/readme-stats.py --write` and commit the result.",
            file=sys.stderr,
        )
        return 1

    print("README stats match the code:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
