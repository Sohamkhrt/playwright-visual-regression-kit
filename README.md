# Local visual regression testing with Playwright

This repository captures deterministic screenshots of the public Playwright TodoMVC demo, compares them locally with committed baseline PNGs, and fails pull requests when more than 0.5% of the compared pixels change. It uses no screenshot-diff service.

## Architecture

- `pages.py` defines four user-visible states: empty, one item, completed item, and a deletion result.
- `conftest.py` launches headless Chromium with a 1280×720 viewport and a fresh context per test. It fixes locale, timezone, scale, color scheme, and reduced-motion preference, and injects CSS that disables animations, transitions, smooth scrolling, and caret blinking.
- `capture.py` drives each state. A missing baseline is created automatically; otherwise a capture goes to `current/`. `--update-baseline` deliberately overwrites every baseline.
- `diff.py` compares RGBA pixels, ignores per-channel changes of 16 or less, applies optional exclusion boxes, calculates the percentage of changed non-masked pixels, and writes a red/yellow visual diff.
- `test_visual_regression.py` parameterizes the same capture/diff path over every state and records machine-readable results.
- `.github/workflows/visual-regression.yml` runs on pull requests, writes a Markdown table to the GitHub job summary, uploads current/diff images, and then fails the job if pytest found a regression.

## Install and run

Python 3.11 is expected.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python capture.py --update-baseline
pytest -v test_visual_regression.py
```

Commit the files in `baselines/`; they are the reviewed visual contract. Generated files under `current/` and `diffs/` are ignored by Git.

The committed sample baselines were generated in the official Playwright 1.55 Ubuntu Noble container to match the Ubuntu GitHub Actions runner. If a developer on another OS sees font-only differences, treat the CI platform as authoritative and regenerate approved baselines on Linux (or change both the workflow and baseline platform together).

## Establishing and updating baselines

On the first run, `python capture.py` creates any missing baseline and captures current images for existing baselines. Prefer the explicit command when approving a complete new visual state:

```bash
python capture.py --update-baseline
```

Review the changed PNGs before committing them. Baselines should normally be updated in the same pull request as the intentional UI change they represent. Never update a baseline merely to make an unexplained failure disappear.

## How comparison works

For every pixel, the largest absolute RGBA channel delta is calculated. A pixel changes only when that value exceeds `DEFAULT_CHANNEL_TOLERANCE = 16`; this absorbs small anti-aliasing and rasterization noise. The test fails when changed pixels exceed `DEFAULT_THRESHOLD_PERCENT = 0.5` of all non-masked pixels. Half a percent is intentionally small enough to detect a shifted control or text change, while allowing a narrow fringe of platform-specific rasterization noise. Tune both values against repeated captures on the CI runner before loosening them.

Image dimension changes count as differences because both images are placed on a canvas large enough for either image. Visual diff PNGs dim unchanged baseline content, paint changed pixels red, and draw a yellow box around the overall changed area.

## Masking known-dynamic regions

`EXCLUSION_BOXES` in `diff.py` maps a snapshot name to `(left, top, right, bottom)` rectangles. Pixels inside those rectangles are excluded from both the changed count and denominator:

```python
EXCLUSION_BOXES = {
    "dashboard": [(1080, 0, 1280, 80)],  # live timestamp
}
```

Keep masks tight and explain each one. A broad mask can hide a real regression. Prefer deterministic test data or hiding a dynamic element with injected CSS when possible.

## Handling flaky diffs

- **Font rendering:** keep the same OS/browser versions in CI and pin Python dependencies. Web fonts should be fully loaded before capture; the capture helper waits for `document.fonts.ready`. For strict cross-platform parity, install and select an identical font everywhere.
- **Anti-aliasing:** neighboring edge pixels can vary slightly between graphics stacks. The channel tolerance ignores tiny color deltas; the percentage threshold handles only the small number of remaining pixels. Do not use a high percentage as a substitute for a sensible channel tolerance.
- **Dynamic content:** freeze clocks and random values in the page when possible. Otherwise add the smallest bounding box to `EXCLUSION_BOXES` for timestamps, rotating ads, or similar content.
- **Full-page screenshots:** page height depends on wrapping and layout, so the viewport must be fixed. Animations, transitions, smooth scrolling, and a blinking caret can put two captures at different frames; the fixture disables them before navigation. Fresh browser contexts prevent local-storage state from leaking between scenarios.

## Deliberately prove the detector

The optional environment hook adds a large red banner after state setup, making a repeatable fake regression without editing the demo site:

```bash
# PowerShell
$env:VISUAL_TEST_MUTATION = "1"
pytest -v test_visual_regression.py
Remove-Item Env:VISUAL_TEST_MUTATION

# bash
VISUAL_TEST_MUTATION=1 pytest -v test_visual_regression.py
```

Inspect `diffs/*_diff.png` after the expected failure. Run pytest normally afterward to verify the repository is green again.

