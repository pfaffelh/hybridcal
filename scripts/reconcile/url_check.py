"""HEAD/GET-check the `url:` of every future event YAML.

We classify the result and return a list of `BrokenUrl` entries to embed
in the weekly PR body. The check never auto-fixes anything — broken URLs
are flagged for human review.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from . import LocalEvent, load_local_events

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 hybridcal-reconciler"
TIMEOUT = 20


@dataclass
class UrlResult:
    event: LocalEvent
    url: str
    status: int | None  # HTTP status, or None on network error
    note: str           # short human-readable reason
    final_url: str = ""

    @property
    def is_broken(self) -> bool:
        # 401/403 typically means "bot-protected, real user is fine".
        # Don't flag those — they create noise.
        if self.status is None:
            return True
        if self.status in (401, 403):
            return False
        return self.status >= 400


def _check_one(le: LocalEvent) -> UrlResult:
    url = (le.data.get("url") or "").strip()
    if not url:
        return UrlResult(le, "", None, "no url field")

    headers = {"User-Agent": UA, "Accept": "*/*"}

    # Try HEAD first.
    try:
        req = Request(url, method="HEAD", headers=headers)
        with urlopen(req, timeout=TIMEOUT) as r:
            return UrlResult(le, url, r.status, "HEAD ok", r.url)
    except HTTPError as e:
        if e.code not in (405, 400):
            # Real HTTP error — record it and don't retry.
            return UrlResult(le, url, e.code, f"HEAD {e.code}")
    except URLError as e:
        # Connection-level failure on HEAD; fall through to GET.
        head_err = f"{type(e).__name__}: {e.reason}"
    except Exception as e:
        head_err = f"{type(e).__name__}: {e}"
    else:
        head_err = ""

    # GET fallback.
    try:
        req = Request(url, method="GET", headers=headers)
        with urlopen(req, timeout=TIMEOUT) as r:
            return UrlResult(le, url, r.status, "GET ok", r.url)
    except HTTPError as e:
        return UrlResult(le, url, e.code, f"GET {e.code}")
    except URLError as e:
        return UrlResult(le, url, None, f"GET {type(e).__name__}: {e.reason}")
    except Exception as e:
        return UrlResult(le, url, None, f"GET {type(e).__name__}: {e}")


def check_all(workers: int = 8) -> list[UrlResult]:
    events = [le for le in load_local_events() if le.is_future]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(_check_one, events))
    return results


def broken(results: list[UrlResult]) -> list[UrlResult]:
    return [r for r in results if r.is_broken]


if __name__ == "__main__":
    rs = check_all()
    bs = broken(rs)
    print(f"checked {len(rs)} future-event URLs, {len(bs)} broken")
    for r in sorted(bs, key=lambda r: (r.event.data.get("format", ""), r.event.path.name)):
        print(f"  {r.note:18s}  {r.event.path.name:55s}  {r.url}")
