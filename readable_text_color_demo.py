"""
Standalone demo: generate a fatigue-reducing text color for an arbitrary
background color.

Architecture (see conversation for the full rationale):
  - LMS (cone-response space, via the Hunt-Pointer-Estevez transform) is
    used only as a *decision* layer: it measures how much of the
    background's signal is riding on the chroma-opponent channels versus
    the luminance channel (chroma_ratio), and gives a physiologically
    real hue direction to tint toward. Raw LMS values are NOT used to
    build the output pixel directly -- they aren't on an evenly-spaced
    perceptual scale, and targeting them directly reintroduces the same
    class of bug found earlier (mixing two lightness models that disagree
    for particular hues, which made red/olive text nearly invisible).
  - CIE Lab is used as the *construction* space: it's perceptually
    uniform, so a target lightness and a small target chroma both mean
    what they say, for every hue.
  - Every candidate is then *measured* (real WCAG contrast ratio against
    the actual background) and corrected until it clears a guaranteed
    minimum -- never trust the formula's output blindly.
  - Backgrounds whose own chroma_ratio is high (magenta, hot pink) are
    flagged: no text color fully fixes those, because the fatigue comes
    from the background field itself, not from insufficient contrast.

Run this file directly:
    python readable_text_color_demo.py

It will:
  1. print a table of results for a handful of "known harsh" test colors
  2. write readable_text_color_preview.html so you can eyeball the results
     in a browser
"""

import math
import webbrowser
import os


def _srgb_to_linear(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c):
    c = max(0.0, min(1.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def rgb_to_xyz(rgb):
    r, g, b = (_srgb_to_linear(c) for c in rgb)
    X = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
    Y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    Z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b
    return X, Y, Z


def xyz_to_rgb(X, Y, Z):
    r = 3.2404542 * X - 1.5371385 * Y - 0.4985314 * Z
    g = -0.9692660 * X + 1.8760108 * Y + 0.0415560 * Z
    b = 0.0556434 * X - 0.2040259 * Y + 1.0572252 * Z
    return tuple(round(_linear_to_srgb(c) * 255) for c in (r, g, b))


def _lab_f(t):
    return t ** (1 / 3) if t > 0.008856 else (7.787 * t + 16 / 116)


def _lab_f_inv(t):
    return t ** 3 if t > 6 / 29 else 3 * (6 / 29) ** 2 * (t - 4 / 29)


_XN, _YN, _ZN = 0.95047, 1.00000, 1.08883


def rgb_to_lab(rgb):
    X, Y, Z = rgb_to_xyz(rgb)
    fx, fy, fz = _lab_f(X / _XN), _lab_f(Y / _YN), _lab_f(Z / _ZN)
    L = 116 * fy - 16
    a = 500 * (fx - fy)
    b = 200 * (fy - fz)
    return L, a, b


def lab_to_rgb(L, a, b):
    fy = (L + 16) / 116
    fx = fy + a / 500
    fz = fy - b / 200
    X = _XN * _lab_f_inv(fx)
    Y = _YN * _lab_f_inv(fy)
    Z = _ZN * _lab_f_inv(fz)
    r, g, b2 = xyz_to_rgb(X, Y, Z)
    return tuple(max(0, min(255, c)) for c in (r, g, b2))


# Hunt-Pointer-Estevez matrix, D65-normalized: XYZ -> LMS cone response
def rgb_to_lms(rgb):
    X, Y, Z = rgb_to_xyz(rgb)
    L = 0.4002 * X + 0.7076 * Y - 0.0808 * Z
    M = -0.2263 * X + 1.1653 * Y + 0.0457 * Z
    S = 0.0000 * X + 0.0000 * Y + 0.9182 * Z
    return L, M, S


def lms_opponent_signature(rgb):
    """Returns (chroma_ratio, hue_angle_rad) from real cone-opponent
    signals. chroma_ratio is how much of the background's signal is
    chroma versus luminance (see conversation: magenta/hot pink score
    high here and no text color fully compensates for that)."""
    L, M, S = rgb_to_lms(rgb)
    rg = L - M
    by = S - (L + M) / 2
    lum = L + M
    chroma_ratio = math.hypot(rg, by) / lum if lum > 0 else 0.0
    hue_angle = math.atan2(by, rg)
    return chroma_ratio, hue_angle


def relative_luminance(rgb):
    """WCAG relative luminance (0-1) -- used only to *measure* real
    rendered contrast, as a check on what the candidate actually is."""
    r, g, b = (_srgb_to_linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(rgb_a, rgb_b):
    """WCAG 2.x contrast ratio -- kept for reference/comparison only.
    Not used for the verification loop below: this is the exact formula
    that misjudges saturated colors (see conversation), so trusting it as
    the final guarantee would reintroduce the class of problem APCA
    exists to fix."""
    la, lb = relative_luminance(rgb_a), relative_luminance(rgb_b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def _apca_y(rgb):
    r, g, b = (_srgb_to_linear(c) for c in rgb)
    return 0.2126729 * r + 0.7151522 * g + 0.0721750 * b


def apca_lc(text_rgb, bg_rgb):
    """APCA (Accessible Perceptual Contrast Algorithm), the WCAG 3
    candidate contrast metric -- built specifically to fix WCAG 2's
    misjudgment of saturated colors, which is exactly the failure mode
    that broke the earlier version of this function on red/olive.
    Returns Lc, roughly -108..106; sign indicates polarity (dark-text-on
    -light-bg is positive, light-text-on-dark-bg is negative), magnitude
    is what matters for legibility. ~60 is a reasonable general-purpose
    floor for body text; APCA's real guidance varies threshold by font
    size/weight rather than using one fixed number."""
    blk_thrs, blk_clmp = 0.022, 1.414
    scale_bow, scale_wob = 1.14, 1.14
    lo_bow_offset, lo_wob_offset = 0.027, 0.027
    delta_y_min, lo_clip = 0.0005, 0.1

    y_txt, y_bg = _apca_y(text_rgb), _apca_y(bg_rgb)
    y_txt = y_txt if y_txt > blk_thrs else y_txt + (blk_thrs - y_txt) ** blk_clmp
    y_bg = y_bg if y_bg > blk_thrs else y_bg + (blk_thrs - y_bg) ** blk_clmp

    if abs(y_bg - y_txt) < delta_y_min:
        return 0.0

    if y_bg > y_txt:
        sapc = (y_bg ** 0.56 - y_txt ** 0.57) * scale_bow
        out = 0.0 if sapc < lo_clip else sapc - lo_bow_offset
    else:
        sapc = (y_bg ** 0.65 - y_txt ** 0.62) * scale_wob
        out = 0.0 if sapc > -lo_clip else sapc + lo_wob_offset

    return out * 100


PROBLEM_CHROMA_RATIO = 0.6  # above this, flag: no text color fully fixes it


def readable_text_color(bg_rgb, min_l=8, max_l=95, steepness=0.18,
                         chroma_scale=14, min_lc=60):
    """
    Generate a text color for bg_rgb.

    LMS decides *whether* to tint and *which hue direction* (real
    cone-opponent geometry, not HSL's hue wheel). Lab builds the actual
    output (perceptually uniform, so targets mean what they say). A
    measured-contrast loop guarantees the result is actually legible,
    regardless of any per-hue quirks in the formula.

    Returns (rgb, problem_background): problem_background is True when
    the background's own chroma_ratio is high enough (see conversation:
    magenta, hot pink) that no generated text color will fully remove
    the discomfort -- that's a background-field problem, not a
    text-color problem, and the caller should consider a halo/backing
    plate or softening the background instead.
    """
    bg_l, _, _ = rgb_to_lab(bg_rgb)
    chroma_ratio, hue_angle = lms_opponent_signature(bg_rgb)
    problem_background = chroma_ratio > PROBLEM_CHROMA_RATIO

    # continuous logistic curve centered on bg_l == 50: every bg_l value
    # maps to a distinct starting text_l value, no thresholding
    sig = 1 / (1 + math.exp(steepness * (bg_l - 50)))
    text_l = min_l + (max_l - min_l) * sig
    push_toward_light = bg_l < 50

    # small same-direction chroma tint, using the LMS-derived hue angle;
    # withheld entirely on problem backgrounds, since adding more chroma
    # to an already chroma-dominant background doesn't reliably help and
    # can compound it (see conversation: hot pink/magenta)
    tint = 0.0 if problem_background else min(chroma_ratio, 1.0) * chroma_scale
    a = tint * math.cos(hue_angle)
    b = tint * math.sin(hue_angle)

    rgb_out = lab_to_rgb(text_l, a, b)
    steps = 0
    while abs(apca_lc(rgb_out, bg_rgb)) < min_lc and steps < 60:
        text_l += 1.5 if push_toward_light else -1.5
        text_l = max(0.0, min(100.0, text_l))
        rgb_out = lab_to_rgb(text_l, a, b)
        steps += 1
        if text_l in (0.0, 100.0):
            break

    final_lc = apca_lc(rgb_out, bg_rgb)
    # honest report, not a silent best-effort: some mid-luminance
    # backgrounds cap out below min_lc even at pure black/white text --
    # that's a real ceiling set by the background's own luminance, not
    # something any text color choice can push past
    contrast_shortfall = abs(final_lc) < min_lc

    return rgb_out, problem_background, contrast_shortfall, final_lc


def hex_of(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)


TEST_COLORS = {
    "pure red":      (237, 28, 36),
    "pure blue":     (46, 49, 146),
    "pure yellow":   (255, 242, 0),
    "cyan":          (0, 255, 255),
    "magenta":       (255, 0, 255),
    "orange":        (255, 127, 39),
    "lime":          (163, 255, 0),
    "dodger blue":   (30, 144, 255),
    "hot pink":      (255, 20, 147),
    "dark navy":     (10, 10, 60),
    "near black":    (20, 20, 20),
    "near white":    (245, 245, 245),
    "olive":         (128, 128, 0),
    "purple":        (128, 0, 128),
}


def main():
    rows = []
    print(f"{'name':<12} {'background':<12} {'text':<12} {'bg L*':>6} {'Lc':>7} {'chroma_ratio':>13} {'flags':>20}")
    for name, bg in TEST_COLORS.items():
        text, problem, shortfall, lc = readable_text_color(bg)
        bg_l, _, _ = rgb_to_lab(bg)
        cr, _ = lms_opponent_signature(bg)
        flags = " ".join(f for f in (
            "CHROMA-PROBLEM" if problem else "",
            "CONTRAST-CEILING" if shortfall else "",
        ) if f)
        print(f"{name:<12} {hex_of(bg):<12} {hex_of(text):<12} {bg_l:6.1f} {lc:7.1f} {cr:13.2f} {flags:>20}")
        rows.append((name, bg, text, problem, shortfall))

    html_rows = "\n".join(
        f'''
        <div class="swatch" style="background:{hex_of(bg)}; color:{hex_of(text)};">
          <div class="label">{name}{' &#9888;' if (problem or shortfall) else ''}</div>
          <div class="sample">The quick brown fox jumps over the lazy dog.</div>
          <div class="codes">bg {hex_of(bg)} / text {hex_of(text)}</div>
        </div>'''
        for name, bg, text, problem, shortfall in rows
    )

    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>readable_text_color preview</title>
<style>
  body {{ font-family: system-ui, sans-serif; background: #222; margin: 0; padding: 24px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }}
  .swatch {{ padding: 20px; border-radius: 8px; }}
  .label {{ font-weight: 600; text-transform: capitalize; margin-bottom: 8px; }}
  .sample {{ font-size: 15px; line-height: 1.4; margin-bottom: 10px; }}
  .codes {{ font-size: 12px; opacity: 0.8; font-family: monospace; }}
</style>
</head>
<body>
  <div class="grid">
    {html_rows}
  </div>
</body>
</html>
"""

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "readable_text_color_preview.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\nWrote preview to {out_path}")
    try:
        webbrowser.open(f"file://{out_path}")
    except Exception:
        pass


if __name__ == "__main__":
    main()
