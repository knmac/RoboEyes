"""Key bindings help overlay rendering and caching."""

from __future__ import annotations

import pygame

KEY_BINDINGS_LINES: list[str] = [
    "Key Bindings",
    "",
    "Esc         Quit",
    "0           Shape: default",
    "1           Shape: tired",
    "2           Shape: angry",
    "3           Shape: smile",
    "4           Shape: squint",
    "5           Shape: sleep",
    "Arrows      Look direction",
    "Space       Center look",
    "b           Blink",
    "q           Wink left",
    "e           Wink right",
    "c           Confused",
    "l           Laugh",
    "s           Breathing (toggle)",
    "f           Fullscreen",
    "?           Toggle help",
]

_cache: dict[tuple[int, int], pygame.Surface] = {}


def _build(width: int, height: int) -> pygame.Surface:
    font_size = max(14, height // 25)
    font = pygame.font.SysFont("monospace", font_size)
    line_height = font.get_linesize()

    rendered = [font.render(line, True, (255, 255, 255)) for line in KEY_BINDINGS_LINES]
    max_width = max(s.get_width() for s in rendered)
    total_height = line_height * len(rendered)

    padding = font_size
    box_w = max_width + padding * 2
    box_h = total_height + padding * 2

    overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    box_x = (width - box_w) // 2
    box_y = (height - box_h) // 2

    pygame.draw.rect(overlay, (0, 0, 0, 180), (box_x, box_y, box_w, box_h))

    y = box_y + padding
    for text_surface in rendered:
        overlay.blit(text_surface, (box_x + padding, y))
        y += line_height

    return overlay


def draw_help_overlay(surface: pygame.Surface) -> None:
    """Blits the cached key bindings overlay centered on the given surface."""
    size = surface.get_size()
    if size not in _cache:
        _cache[size] = _build(*size)
    surface.blit(_cache[size], (0, 0))


def clear_cache() -> None:
    """Clears the overlay cache (call on resolution change)."""
    _cache.clear()
