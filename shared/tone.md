# Tone Rules for Outward-Facing Text

Shared reference for any skill or draft that produces text other people read:
post-mortems, PR descriptions, team-channel posts, replies to bug reports or
review feedback, weekly digests, release notes, blog posts.

Load this file whenever drafting such text. The goal: honest substance,
non-defensive narrative, zero invented facts.

## 1. Frame gaps as scope, not failure

If a feature shipped and worked in the context it was tested in but didn't
cover a deployment/usage path that wasn't validated pre-ship, frame it as
scope extension — not regression.

| Do NOT write                         | Write instead                                                                     |
| ------------------------------------ | --------------------------------------------------------------------------------- |
| "was broken" / "broke in production" | "did not cover path X"                                                            |
| "silently non-functional"            | "silent under context Y — no observable side-effect assertion"                    |
| "regression"                         | "gap exposed by enterprise validation"                                            |
| "failed in every real deployment"    | "worked for interactive installs; SCCM/SYSTEM path required additional hardening" |
| "the feature never worked"           | "the feature worked in the tested context; coverage was extended to context X"    |
| "was silently no-op"                 | "silent under SYSTEM context; observable-assert gap"                              |

**Technical root-cause analysis stays unchanged.** This rule is about
narrative, not substance. Describe the actual plumbing bug exactly as it was —
just don't wrap it in "we shipped a broken feature" language.

**Honest but forward-looking**: it is OK (and correct) to say "we did not
validate against the SYSTEM-context path before shipping" once, in a Context
or Objective section. That's honest scoping, not self-flagellation. Don't
repeat that framing in every section.

## 2. No defensive lead

When responding to a raised issue, bug report, or critical review comment:
acknowledge and investigate first ("let me look", "good catch, checking"),
explain after the facts are confirmed. Context and justification come second,
never first. If the report turns out wrong, show the evidence neutrally —
never "as I already said" / "that's not how it works".

## 3. Anonymize

Never name a customer. Use "an enterprise customer deploying via SCCM" /
"a field report from a managed-desktop environment". Internal ticket IDs
(PROD-595) are OK; external customer tracker IDs are NOT.

## 4. Real numbers only

No invented metrics — no estimated hours saved, no speculated user counts.
Only numbers from actual logs, error messages, tickets, git history, or
documented sources. "Reduced startup hangs" beats a made-up percentage.

## 5. Reread gate

Before any text is sent or published, reread the full draft once, end to end,
as the recipient. Then run the mechanical check:

```
grep -inE 'broken|regression|silently non-functional|never worked|failed in production|was a bug|shipped broken' <draft>
```

Every hit needs review — either rewrite it per the table above, or consciously
confirm it's inside a technical root-cause description where it's accurate
and necessary.
