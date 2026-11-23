#!/usr/bin/env python3
"""Search the web through a self-hosted SearXNG instance (JSON API, stdlib only).

Instance URL order: --url, then $SEARXNG_URL, then `url:` in local-config.yml
next to this script.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

CONFIG = os.path.join(os.path.dirname(os.path.realpath(__file__)), "local-config.yml")
TIME_RANGES = ("day", "week", "month", "year")


def instance_url(cli_url):
    if cli_url:
        return cli_url
    if os.environ.get("SEARXNG_URL"):
        return os.environ["SEARXNG_URL"]
    try:
        with open(CONFIG, encoding="utf-8") as fh:
            for line in fh:
                key, _, value = line.partition(":")
                if key.strip() == "url" and value.strip():
                    return value.strip().strip("'\"")
    except FileNotFoundError:
        pass
    sys.exit(
        "error: no SearXNG URL. Set SEARXNG_URL, pass --url, or write\n"
        f"  url: http://<host>:<port>\nto {CONFIG}"
    )


def search(base, args):
    params = {"q": args.query, "format": "json", "pageno": args.page}
    if args.categories:
        params["categories"] = args.categories
    if args.engines:
        params["engines"] = args.engines
    if args.lang:
        params["language"] = args.lang
    if args.time_range:
        params["time_range"] = args.time_range
    if args.safesearch is not None:
        params["safesearch"] = args.safesearch
    url = base.rstrip("/") + "/search?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        hint = " (is 'json' listed in search.formats in settings.yml?)" if exc.code == 403 else ""
        sys.exit(f"error: HTTP {exc.code} from {base}{hint}")
    except (urllib.error.URLError, TimeoutError) as exc:
        sys.exit(f"error: cannot reach {base}: {getattr(exc, 'reason', exc)}")


def trim(text, size):
    text = " ".join((text or "").split())
    return text if len(text) <= size else text[: size - 1] + "…"


def render(data, limit, snippet):
    out = []
    for ans in data.get("answers") or []:
        text = ans.get("answer") if isinstance(ans, dict) else ans
        if text:
            out.append(f"ANSWER: {trim(str(text), snippet * 2)}")
    for box in data.get("infoboxes") or []:
        out.append(f"INFOBOX [{box.get('engine', '?')}]: {box.get('infobox', '')}")
        if box.get("content"):
            out.append(f"  {trim(box['content'], snippet * 2)}")
        for link in (box.get("urls") or [])[:3]:
            out.append(f"  {link.get('title', '')}: {link.get('url', '')}")
    results = (data.get("results") or [])[:limit]
    for i, res in enumerate(results, 1):
        engines = ",".join(res.get("engines") or [res.get("engine", "?")])
        date = f" | {res['publishedDate'][:10]}" if res.get("publishedDate") else ""
        out.append(f"{i}. {trim(res.get('title'), 120)}")
        out.append(f"   {res.get('url', '')}")
        out.append(f"   [{engines}{date}] {trim(res.get('content'), snippet)}")
    if not results and not out:
        out.append("No results.")
    if data.get("suggestions"):
        out.append("SUGGESTIONS: " + "; ".join(data["suggestions"][:5]))
    if data.get("corrections"):
        out.append("CORRECTIONS: " + "; ".join(data["corrections"][:3]))
    print("\n".join(out))
    bad = data.get("unresponsive_engines") or []
    if bad:
        print("unresponsive: " + ", ".join(f"{e} ({why})" for e, why in bad), file=sys.stderr)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("query", help="search text; SearXNG bangs work, e.g. '!gh fastapi'")
    p.add_argument("-n", "--limit", type=int, default=10, help="results to print (default 10)")
    p.add_argument("-c", "--categories", help="e.g. general,news,it,science,images,videos,map")
    p.add_argument("-e", "--engines", help="comma list, e.g. 'brave,wikipedia'")
    p.add_argument("-l", "--lang", help="language code, e.g. en, pt-BR (default: instance auto)")
    p.add_argument("-t", "--time-range", choices=TIME_RANGES)
    p.add_argument("-p", "--page", type=int, default=1)
    p.add_argument("-s", "--safesearch", type=int, choices=(0, 1, 2))
    p.add_argument("--snippet", type=int, default=240, help="snippet length in chars (default 240)")
    p.add_argument("--json", action="store_true", help="print the raw JSON response")
    p.add_argument("--timeout", type=float, default=30.0)
    p.add_argument("--url", help="SearXNG base URL (overrides env and config)")
    args = p.parse_args()

    data = search(instance_url(args.url), args)
    if args.json:
        json.dump(data, sys.stdout, ensure_ascii=False, indent=1)
        print()
    else:
        render(data, args.limit, args.snippet)


if __name__ == "__main__":
    main()
