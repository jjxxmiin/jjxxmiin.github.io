# ManimGL ratio loop

This isolated example uses the original [3Blue1Brown ManimGL](https://github.com/3b1b/manim), whose PyPI package is `manimgl` (not `manim`). It renders a silent six-second 16:9 loop that explains `268 / 285 ≈ 94%` with exactly 285 cells.

## Render

```bash
automation/manim/setup.sh
automation/manim/render.sh
```

The final web assets are written to:

- `assets/media/manim/ratio-268-of-285.mp4`
- `assets/media/manim/ratio-268-of-285-poster.png`

Intermediate Manim files and the local environment remain under ignored paths in `automation/manim/`.

## Why setup uses a local Conda prefix

ManimGL needs Pango/Cairo development metadata to build `manimpango`. This host has their runtime libraries but not the required `pangocairo.pc`, so an ordinary Python venv cannot install it. `setup.sh` brings Pango, Cairo, HarfBuzz, GLib, and pkg-config into `automation/manim/.conda/`; it does not modify system packages.

LaTeX is deliberately not required. The scene uses ManimGL `Text` and geometric objects, so it also works on hosts without TeX or `dvisvgm`.

Headless Linux rendering uses Xvfb because ManimGL's default standalone ModernGL context opens an X display. The script automatically uses the existing display when one is available.
