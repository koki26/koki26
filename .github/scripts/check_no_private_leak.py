#!/usr/bin/env python3
"""Refuse to publish a metrics panel that contains anything but aggregate labels.

The panels are meant to expose only totals (repo counts, byte counts, language
names). A future metrics version, or a stray plugin being switched on, could
start emitting private repository names, commit subjects or code. This gate
runs before the SVGs are committed, so such a change fails the workflow
instead of publishing.

Usage: check_no_private_leak.py <private-names-file> <svg> [svg ...]
"""
import re
import sys

# Longest legitimate label observed is "Contributed to 29 repositories" (30).
MAX_LABEL = 60

# Every legitimate label is prose, a number, a unit or a language name. None
# contain brackets, colons, underscores or operators, so any string carrying
# them is code, a path or a commit subject rather than an aggregate.
ALLOWED = re.compile(r"^[A-Za-z0-9 .,%+\-~#'/&]*$")


def visible_strings(path):
    """Every string a viewer or scraper could read out of the SVG."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        svg = fh.read()
    svg = re.sub(r"<(style|script)[^>]*>.*?</\1>", "", svg, flags=re.S)
    svg = re.sub(r"(data:|url\()[^\"')\s]+", "", svg)  # drop embedded blobs
    found = re.findall(r">([^<>]+)<", svg)
    found += re.findall(r"(?:title|alt|aria-label|data-[a-z-]+)=\"([^\"]+)\"", svg)
    return [s.strip() for s in found if s.strip()]


def main():
    if len(sys.argv) < 3:
        print("usage: check_no_private_leak.py <names-file> <svg> [svg ...]")
        return 2

    with open(sys.argv[1], encoding="utf-8") as fh:
        names = [n.strip() for n in fh if n.strip()]

    violations = []
    for path in sys.argv[2:]:
        for text in visible_strings(path):
            for name in names:
                if name.lower() in text.lower():
                    violations.append((path, "private repo name %r" % name, text))
            if len(text) > MAX_LABEL:
                violations.append((path, "string over %d chars" % MAX_LABEL, text))
            elif not ALLOWED.match(text):
                bad = "".join(sorted(set(c for c in text if not ALLOWED.match(c))))
                violations.append((path, "disallowed character(s) %r" % bad, text))

    if violations:
        for path, why, text in violations:
            print("::error file=%s::%s in: %s" % (path, why, text[:200]))
        print("FAILED: %d violation(s); refusing to publish" % len(violations))
        return 1

    print("OK: %d names checked against %d file(s); only aggregate labels found"
          % (len(names), len(sys.argv) - 2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
