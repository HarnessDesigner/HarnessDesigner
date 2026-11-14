# harness_designer/resources.py

I/O and network helpers. None of this is on a per-frame path; the concern is blocking the calling thread.

## Line 135-202 (`requests_get`) — builds a CookieJar and scans every stored cookie per request
For each request it creates a new `CookieJar` and loops over `COOKIES` by domain, copying matching cookies in. Fine at the request rates used (one per catalog part download). It calls `requests.get` (a new connection each time) rather than a shared `requests.Session`, so it does not reuse TLS connections: a batch of downloads from one host pays the handshake each time. A `Session` per host would cut that; the TE site needs its cookies handled by hand here, so test any change against it.

A latent bug sits next to it: the `except RequestException` branch reads `err.response.status_code`, and `err.response` is `None` for a connection error or a timeout, so the handler itself raises `AttributeError`. Not a performance point, but it turns a retryable network error into a crash on a worker thread.

## Line 395-500 (`collect_resource`) — SQL round trips before any work
It issues a `SELECT value FROM settings` per call and another `SELECT extension FROM file_types` per local file. Over MySQL each is a network round trip. Both tables are tiny and almost never change, so a small module-level cache (filled on first use) would remove them; the memory cost is a few rows.

## Line 206-275 (`_download_model`), 317-385 (`_download_image`) — extension lookup per download
Each runs its own `file_types` SELECT (flagged as inside a loop). The same cache applies.

## Image reformat with Pillow
A downloaded image is opened, re-formatted into a 256 x 256 PNG and re-saved, then the original is removed. That is a full decode, resize and encode per image; acceptable for a one-off download. The working copy is released when `img` goes out of scope.
