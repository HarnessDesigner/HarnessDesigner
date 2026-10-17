# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The JavaScript that records the page's own ``fetch`` / ``XMLHttpRequest``
calls (the XHR traffic the Network tab shows).

It is injected into the page's JS world at document creation, in every
frame, and wraps the two request APIs. Each finished request is sent to
Python as one JSON string through a ``QWebChannel`` object named
:data:`BRIDGE_NAME` whose only slot is ``record(str)``. The wrapper hands
the page its original promise / events untouched, and everything it does is
inside ``try``/``catch`` -- a capture problem must never break the page
being scraped.

Not captured (see SCRAPER_DESIGN.md): requests made by Web or Service
Workers, requests made before this script runs, ``sendBeacon``, and
non-XHR resources (images, scripts, CSS). Binary response bodies are
skipped; text bodies longer than :data:`MAX_BODY_CHARS` are cut short and
flagged.
"""

from .. import check_types as _check_types

BRIDGE_NAME = 'bridge'

# Longest response body, in characters, the page-side script keeps.
MAX_BODY_CHARS = 2_000_000

# Records waiting for the channel to come up are dropped past this many.
_MAX_QUEUED = 500

_SOURCE = r'''
(function () {
  'use strict';
  if (typeof qt === 'undefined' || typeof QWebChannel === 'undefined') { return; }
  if (window.__hdCapture) { return; }
  Object.defineProperty(window, '__hdCapture', {value: true, enumerable: false});

  var MAX_BODY = __MAX_BODY__;
  var MAX_QUEUED = __MAX_QUEUED__;
  var TEXT_TYPE = /(^$|text\/|json|xml|javascript|html|x-www-form-urlencoded|csv|graphql)/i;
  var queue = [];
  var bridge = null;

  function post(record) {
    try {
      record.pageUrl = location.href;
      record.userAgent = navigator.userAgent;
      record.topFrame = (window === window.top);
      var text = JSON.stringify(record);
      if (bridge) { bridge.record(text); }
      else if (queue.length < MAX_QUEUED) { queue.push(text); }
    } catch (e) {}
  }

  try {
    new QWebChannel(qt.webChannelTransport, function (channel) {
      bridge = channel.objects.__BRIDGE__;
      while (queue.length) { bridge.record(queue.shift()); }
    });
  } catch (e) { return; }

  function headersToObject(source, into) {
    var out = into || {};
    if (!source) { return out; }
    try {
      if (typeof Headers !== 'undefined' && source instanceof Headers) {
        source.forEach(function (value, key) { out[key] = value; });
      } else if (Array.isArray(source)) {
        source.forEach(function (pair) { out[pair[0]] = pair[1]; });
      } else {
        Object.keys(source).forEach(function (key) { out[key] = String(source[key]); });
      }
    } catch (e) {}
    return out;
  }

  // {text, kind} for the body kinds that can be written down as text.
  function bodyToText(body) {
    if (body === null || body === undefined) { return {text: null, kind: ''}; }
    if (typeof body === 'string') { return {text: body, kind: ''}; }
    if (typeof URLSearchParams !== 'undefined' && body instanceof URLSearchParams) {
      return {text: body.toString(), kind: 'urlencoded'};
    }
    if (typeof FormData !== 'undefined' && body instanceof FormData) {
      var parts = [];
      body.forEach(function (value, key) {
        var text = (typeof value === 'string') ? value : '[file ' + value.name + ']';
        parts.push(encodeURIComponent(key) + '=' + encodeURIComponent(text));
      });
      return {text: parts.join('&'), kind: 'multipart'};
    }
    return {text: null, kind: ''};
  }

  function cut(text) {
    if (text !== null && text.length > MAX_BODY) { return {text: text.slice(0, MAX_BODY), truncated: true}; }
    return {text: text, truncated: false};
  }

  function parseResponseHeaders(raw) {
    var out = {};
    raw.trim().split(/[\r\n]+/).forEach(function (line) {
      var at = line.indexOf(':');
      if (at > 0) { out[line.slice(0, at).trim().toLowerCase()] = line.slice(at + 1).trim(); }
    });
    return out;
  }

  // ---- fetch ---------------------------------------------------------------
  var originalFetch = window.fetch;
  if (typeof originalFetch === 'function') {
    window.fetch = function (input, init) {
      var started = Date.now();
      var meta = null;
      var requestClone = null;
      try {
        var isRequest = (typeof Request !== 'undefined') && (input instanceof Request);
        var method = ((init && init.method) || (isRequest ? input.method : 'GET')).toUpperCase();
        var headers = {};
        if (isRequest) { headersToObject(input.headers, headers); }
        if (init && init.headers) { headersToObject(init.headers, headers); }
        var body = (init && init.body !== undefined) ? bodyToText(init.body) : {text: null, kind: ''};
        if (isRequest && !(init && init.body !== undefined) && method !== 'GET' && method !== 'HEAD') {
          requestClone = input.clone();
        }
        meta = {
          kind: 'fetch', method: method, url: new URL(isRequest ? input.url : String(input), location.href).href,
          requestHeaders: headers, requestBody: body.text, requestBodyKind: body.kind
        };
      } catch (e) { meta = null; }

      var promise = originalFetch.apply(this, arguments);
      if (!meta) { return promise; }

      promise.then(function (response) {
        try {
          var responseHeaders = {};
          response.headers.forEach(function (value, key) { responseHeaders[key] = value; });
          var type = response.headers.get('content-type') || '';
          var length = parseInt(response.headers.get('content-length') || '0', 10);
          var wantsBody = TEXT_TYPE.test(type) && !/event-stream/i.test(type) && !(length > MAX_BODY * 4);
          var bodyRead = wantsBody ? response.clone().text() : Promise.resolve(null);
          var requestRead = requestClone ? requestClone.text() : Promise.resolve(meta.requestBody);
          Promise.all([bodyRead, requestRead]).then(function (results) {
            var trimmed = cut(results[0]);
            meta.requestBody = results[1];
            meta.status = response.status;
            meta.responseHeaders = responseHeaders;
            meta.responseBody = trimmed.text;
            meta.responseTruncated = trimmed.truncated;
            meta.durationMs = Date.now() - started;
            post(meta);
          }, function () {});
        } catch (e) {}
      }, function (error) {
        try {
          meta.status = 0;
          meta.responseHeaders = {};
          meta.responseBody = null;
          meta.error = String(error);
          meta.durationMs = Date.now() - started;
          post(meta);
        } catch (e) {}
      });
      return promise;
    };
  }

  // ---- page source ---------------------------------------------------------
  // Downloads the current page again with this browser's cookies and hands
  // the text to Python. Uses the ORIGINAL fetch so the request does not
  // show up in the Network list.
  Object.defineProperty(window, '__hdPageSource', {enumerable: false, value: function () {
    if (!bridge || typeof originalFetch !== 'function') { return false; }
    var url = location.href;
    originalFetch.call(window, url, {credentials: 'include'}).then(function (response) {
      return response.text();
    }).then(function (text) {
      bridge.pageSource(url, cut(text).text);
    }, function () {
      bridge.pageSource(url, '');
    });
    return true;
  }});

  // ---- XMLHttpRequest ------------------------------------------------------
  var proto = XMLHttpRequest.prototype;
  var originalOpen = proto.open;
  var originalSetHeader = proto.setRequestHeader;
  var originalSend = proto.send;

  proto.open = function (method, url) {
    try {
      this.__hd = {kind: 'xhr', method: String(method).toUpperCase(),
                   url: new URL(String(url), location.href).href, requestHeaders: {}};
    } catch (e) { this.__hd = null; }
    return originalOpen.apply(this, arguments);
  };

  proto.setRequestHeader = function (name, value) {
    try { if (this.__hd) { this.__hd.requestHeaders[name] = value; } } catch (e) {}
    return originalSetHeader.apply(this, arguments);
  };

  proto.send = function (body) {
    var self = this;
    var meta = this.__hd;
    if (meta) {
      try {
        var sent = bodyToText(body);
        meta.requestBody = sent.text;
        meta.requestBodyKind = sent.kind;
        var started = Date.now();
        this.addEventListener('loadend', function () {
          try {
            var text = null;
            if (self.responseType === '' || self.responseType === 'text') { text = self.responseText; }
            else if (self.responseType === 'json') { text = JSON.stringify(self.response); }
            else if (self.responseType === 'document' && self.response && self.response.documentElement) {
              text = self.response.documentElement.outerHTML;
            }
            var trimmed = cut(text);
            meta.status = self.status;
            meta.responseHeaders = parseResponseHeaders(self.getAllResponseHeaders() || '');
            meta.responseBody = trimmed.text;
            meta.responseTruncated = trimmed.truncated;
            meta.durationMs = Date.now() - started;
            if (self.status === 0) { meta.error = 'request failed or was aborted'; }
            post(meta);
          } catch (e) {}
        });
      } catch (e) {}
    }
    return originalSend.apply(this, arguments);
  };
})();
'''


@_check_types.do
def hook_source() -> str:
    """The capture script with its limits filled in."""
    return (_SOURCE
            .replace('__MAX_BODY__', str(MAX_BODY_CHARS))
            .replace('__MAX_QUEUED__', str(_MAX_QUEUED))
            .replace('__BRIDGE__', BRIDGE_NAME))
