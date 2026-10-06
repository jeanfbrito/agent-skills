---
name: why
description: 'Investigates why code, a setting, or a behavior is the way it is. Examples: design rationale, a regression''s origin, a threshold''s source, dead-looking code. It anchors on git history, then queries every connected evidence source (GitHub PRs, Jira, Confluence, Rocket.Chat, Zoho Desk, prior-session memory). It answers with each claim tagged by confidence. Triggered by "/why", "why is this like this", "why did we do X", "why was this added", "what motivated this", "where did this number come from", "when did this break and why".'
---

# Why

Answer what forces shaped a piece of code. `how` questions (what the code does)
are answered by reading it. `why` lives in commits, PRs, tickets, docs, and
chat, all incomplete and sometimes contradictory. The deliverable is a cited
answer that keeps what the record says apart from what you infer.

Adapted from [cursor/plugins](https://github.com/cursor/plugins) `pstack/why`
(MIT License), reduced to the sources this workspace has.

## 1. Target and question

Name the target (file and lines, symbol, setting, behavior) and the question
(rationale, regression origin, threshold source, dead code, history). If the
request is vague, state your reading in one line and proceed. A hypothesis in
the question ("I assume it's for performance?") is one candidate to test, not
a conclusion to confirm.

## 2. Code anchor

Build it before any other source. Every later query keys off it.

```bash
git blame -L <start>,<end> -- <file>
git log --follow --format='%h %ad %an %s' --date=short -- <file> | head -30
git log -S'<literal>' --format='%h %ad %s' --date=short   # when a value appeared
gh pr view <n> --json title,body,author,mergedAt,comments,reviews
```

Collect:

- Paths and lines.
- Symbols.
- The commits that introduced and last changed the target.
- PR numbers.
- Every ticket key in those commits and PRs (`CORE-`, `SUP-`, other Jira keys).

Recency bias is the common failure. The last commit is rarely where the shape
came from. Walk back to the introducing change.

## 3. Query every connected source

One line per source in the final "Sources consulted", including the ones that
returned nothing and the ones unavailable, with the reason. A search that finds
nothing is a result.

| Source | What it uniquely holds | How |
| --- | --- | --- |
| Git + GitHub | review-time rationale, reverts, linked issues | step 2 commands, plus PR comments and review threads |
| Jira | the product or support forcing function | JQL on the ticket keys from step 2, then on project/component/fixVersion. Keyword text search misses tickets |
| Confluence | written design rationale, post-mortems | CQL search on the feature, symbol, or ticket key |
| Rocket.Chat | deliberation that never reached a doc | `rocket-cli` search_messages on the ticket key, symbol, or feature name |
| Zoho Desk | the customer report behind a defensive fix | ticket lookup by SUP key or customer symptom, when the connector is enabled |
| Session memory | what earlier sessions learned | `mm_search`, project memory, `lessons.md` |
| Upstream source | the server or library behavior the code reacts to | GitNexus over the indexed repo, plus the library's source at its pinned version |

Run the source queries yourself for a narrow target. For a broad history
question, dispatch one read-only agent per source in a single message. Give
each agent the anchor and the question. Each agent returns findings with
citations, and an explicit "nothing found for <queries>" when its search is
empty. If a connector is
disabled, name it as a gap rather than guessing what it would say.

Defensive code (retries, timeouts, null guards, feature flags, rate limits)
usually traces to an incident. Search for the incident, ticket, or error that
preceded the commit.

## 4. Grade every claim

| Tier | Meaning | Phrasing |
| --- | --- | --- |
| Direct | an author wrote down the reason (PR body, ticket, comment, doc, chat) | "This exists because X [cite]." |
| Supported | several indirect sources converge | "The evidence points to X: [A], [B]." |
| Inferred | a reasonable reading nothing states | "Given A and B, X seems likely because C." |
| Speculative | plausible, thin evidence, rivals fit as well | "One possibility is X. No direct evidence." |
| Unknown | searched, not found | "Searched <sources> for <queries>. Nothing found." |

"because", "was designed to", "the team decided", and "fixes" claim Direct or
Supported confidence and need a citation beside them. When sources contradict,
present both with citations. Do not retrofit a clean rationale onto messy
history, and do not read absence of evidence as evidence of absence.

## 5. Answer

Use these sections, and drop any that are empty:

- **Question**
- **Code in question** (file:line, introducing commit)
- **What we found** (Direct and Supported, cited)
- **What we can infer**
- **Competing hypotheses**
- **What we don't know**
- **Sources consulted** (one line per source)
- **Confidence summary**

If the question precedes a change, end with **Preserve / Change / Avoid / Risk**.
Preserve is what the history says must keep holding. Change is what is free to
change. Avoid is what was tried and failed. Risk is what could regress.

Jira, Zoho, and chat content is internal: keep it out of anything public (PR
bodies, commit messages, public issues).
