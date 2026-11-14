# harness_designer/process/clean_creds/__init__.py

## Line 8-15 — platform switch at import
On Windows, `run` is the Windows credential cleaner. Elsewhere it is a no-op. The choice is made once at import. Fine.
