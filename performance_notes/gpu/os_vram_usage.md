# harness_designer/gpu/os_vram_usage.py

## Line 40-60 (`get_current_usage_bytes`) — platform dispatch per call
Checks `sys.platform` and forwards. Trivial.

## Line 63-73 (`_windows_usage`) — imports the DXGI module on each call
`from . import _dxgi_win` runs inside the function. After the first import the module is cached, so each call costs one import lookup. Fine.

## Line 76-108 (`_linux_usage`) — reads every open file descriptor's `fdinfo` on each call
Lists `/proc/self/fdinfo`, opens every entry, and reads its content to look for `drm-total-memory`. A process with many open file descriptors does one `open` and `read` per descriptor per call. Called once per GPU detection. Acceptable on demand; if it were ever polled, it would be the expensive part.

**Typing (fixed in this pass):** the three functions now declare `int | None` returns.
