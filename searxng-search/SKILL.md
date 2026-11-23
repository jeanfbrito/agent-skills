---
name: searxng-search
description: Searches the web through the user's self-hosted SearXNG instance with its JSON API and prints numbered results with title, URL, engines and snippet. Use for web lookups, documentation, error messages, news and recent events, when the user asks (in English or Portuguese) to search with SearXNG, or when the built-in WebSearch is unavailable. Triggered by "/searxng-search".
---

# SearXNG search

Search the web through the user's own SearXNG instance.
The helper uses only the Python standard library. It sends GET requests only.

## Setup

The helper finds the instance URL in this order:

1. The `--url` argument.
2. The `SEARXNG_URL` environment variable.
3. The `url:` line in `~/Github/agent-skills/searxng-search/local-config.yml`.

Git ignores `local-config.yml`. The file has one line:

```yaml
url: http://<host>:<port>
```

If you set no URL, the helper stops and shows this instruction.
Ask the user for the URL. Do not guess an address.

The instance must allow the JSON format.
`settings.yml` must list `json` under `search.formats`.
Otherwise the instance returns HTTP 403.

## Search

```sh
python3 ~/Github/agent-skills/searxng-search/search.py "<query>"
```

Options:

| Option | Use |
| --- | --- |
| `-n 20` | Print more results. The default is 10. |
| `-c news` | Search one category: `general`, `news`, `it`, `science`, `images`, `videos`, `map`. |
| `-t week` | Keep results from the last `day`, `week`, `month` or `year`. |
| `-e brave,wikipedia` | Use only these engines. |
| `-l en` | Set the result language. The default is the instance setting. |
| `-p 2` | Show the next page of results. |
| `--snippet 500` | Show longer snippets. |
| `--json` | Print the raw JSON response. Pipe it to a script, not to the conversation. |

Use the default `general` category for documentation and error messages.
The `it` category returns mostly package registries, for example Docker Hub.
Engines that cannot filter by date do not run with `-t`, so `-t` can give no results.

SearXNG bangs work in the query. Examples: `!wp proxmox` (Wikipedia),
`!gh fastapi` (GitHub), `!osm Lisbon` (OpenStreetMap), `!so asyncio` (Stack Overflow).

## Procedure

1. Write a short, specific query. Use the words that the target page probably has.
2. Run the helper. Read the numbered results.
3. If the results are weak, change the query, the category, or the time range. Do not repeat the same query.
4. To read a page, fetch its URL with the fetch tool of the session.
   A snippet is not the page. Do not quote a fact from a snippet only.
5. In the answer, cite each URL that supports a claim, as a Markdown link.

## Output

The helper prints, in this order:

- `ANSWER:` lines, if an engine gave a direct answer.
- `INFOBOX` blocks, for example from Wikipedia or Wikidata.
- Numbered results: title, URL, then `[engines | date] snippet`.
- `SUGGESTIONS:` and `CORRECTIONS:`, if the instance gave them.

The helper writes engines that did not respond to stderr, for example
`unresponsive: duckduckgo (CAPTCHA)`. The other engines still return results.
Report an unresponsive engine only when the result set is empty or thin.

## Errors

| Message | Cause | Action |
| --- | --- | --- |
| `no SearXNG URL` | The setup has no URL. | Ask the user for the URL. Write it to `local-config.yml`. |
| `cannot reach` | The instance is down, or the network is not the LAN. | Tell the user. Use the built-in WebSearch if the user agrees. |
| `HTTP 403` | The JSON format is off. | Tell the user to add `json` to `search.formats`. |
| `HTTP 429` | The bot limiter blocked the client. | Tell the user. The limiter setting belongs to the instance owner. |
| `No results.` | No engine found a match. | Change the query, or remove `-c`, `-t` or `-e`. |

## Privacy

The instance sends the query to the upstream engines. The engines see the
instance address, not the address of this machine.
Do not put secrets, credentials or customer data in a query.
