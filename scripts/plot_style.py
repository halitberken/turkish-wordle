"""Shared matplotlib look for the result charts (light surface, hairline grid, thin rounded bars)."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.path import Path as MplPath  # noqa: E402
from matplotlib.patches import PathPatch  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
# Categorical slots in fixed order (validated for colour-vision deficiency).
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]

DPI = 200
BAR_RADIUS_IN = 4 / 96  # 4 CSS px


def new_figure(width_in: float, height_in: float, rect: tuple[float, float, float, float]):
    """Figure with one axes at a fixed position (so pixel sizes can be converted to data units)."""
    fig = plt.figure(figsize=(width_in, height_in), dpi=DPI, facecolor=SURFACE)
    ax = fig.add_axes(rect, facecolor=SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE)
    ax.tick_params(colors=INK_MUTED, length=0, labelsize=9)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    return fig, ax


def title(fig, text: str, subtitle: str = "") -> None:
    fig.text(0.02, 0.95, text, fontsize=13, fontweight="bold", color=INK, va="top")
    if subtitle:
        fig.text(0.02, 0.885, subtitle, fontsize=9.5, color=INK_SECONDARY, va="top")


def rounded_bars(ax, xs, heights, width: float, colors) -> None:
    """Vertical bars with a rounded top (data end) and a square base.

    Call after the axes limits are final: the corner radius is converted from
    inches to data units with the current limits.
    """
    fig = ax.figure
    bbox = ax.get_position()
    x_lo, x_hi = ax.get_xlim()
    y_lo, y_hi = ax.get_ylim()
    rx_full = BAR_RADIUS_IN * (x_hi - x_lo) / (bbox.width * fig.get_figwidth())
    ry_full = BAR_RADIUS_IN * (y_hi - y_lo) / (bbox.height * fig.get_figheight())
    k = 0.5523  # cubic Bézier approximation of a quarter circle
    for x, h, color in zip(xs, heights, colors):
        if h <= 0:
            continue
        x0, x1 = x - width / 2, x + width / 2
        rx, ry = min(rx_full, width / 2), min(ry_full, h)
        verts = [
            (x0, 0), (x1, 0), (x1, h - ry),
            (x1, h - ry + k * ry), (x1 - rx + k * rx, h), (x1 - rx, h),
            (x0 + rx, h),
            (x0 + rx - k * rx, h), (x0, h - ry + k * ry), (x0, h - ry),
            (x0, 0),
        ]
        codes = [MplPath.MOVETO, MplPath.LINETO, MplPath.LINETO,
                 MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
                 MplPath.LINETO,
                 MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
                 MplPath.CLOSEPOLY]
        ax.add_patch(PathPatch(MplPath(verts, codes), facecolor=color, edgecolor="none"))


def legend(ax, entries: list[tuple[str, str]], loc: str = "upper right") -> None:
    """Square swatches with ink-coloured text."""
    from matplotlib.patches import Patch

    handles = [Patch(facecolor=color, edgecolor="none", label=label) for label, color in entries]
    leg = ax.legend(handles=handles, loc=loc, frameon=False, fontsize=9,
                    handlelength=0.9, handleheight=0.9, labelcolor=INK_SECONDARY)
    leg.set_zorder(5)


def save(fig, path) -> None:
    fig.savefig(path, dpi=DPI, facecolor=SURFACE)
    plt.close(fig)
