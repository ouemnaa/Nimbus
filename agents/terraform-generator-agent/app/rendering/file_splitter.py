from __future__ import annotations

from collections import defaultdict


def group_blocks_by_file(blocks: list[tuple[str, str]]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for file, block in blocks:
        grouped[file].append(block)
    return dict(grouped)
