# Upstream

Vendored from https://github.com/danyuchn/asd-ste100-skill at commit
`32511c6` (2026-10-04), MIT License (see `LICENSE`). The repository README is
not copied. ASD-STE100 itself is a copyright and trademark of ASD, Brussels.
The skill paraphrases the rule categories and does not contain the official
dictionary. Request the standard at https://www.asd-ste100.org/STE_downloads.html.

## Local changes

- `scripts/ste-lint.py`: the upstream linter measured sentence length one
  physical line at a time, so a sentence hard-wrapped across lines was never
  flagged. Wrapped lines now join into the paragraph or list item they form
  before the length check (`_prose_blocks`). Table cells keep the upstream
  per-cell check. Selftest cases cover wrapped prose, list items, headings,
  blank lines, and fenced code.

- `scripts/ste-lint.py` `plain-word` rule (advisory): flags words and phrases
  from `references/plain-words.tsv`, the public-domain list from the US Federal
  Plain Language Guidelines (credit: PLAIN, www.plainlanguage.gov), and skips
  `references/software-terms.txt`. `--allow` adds project terms. A phrasal-verb
  suggestion yields to a one-word one from the same row (STE Rule 9.3).
- `scripts/ste-pdf-index.py`: writes a page map for the user's own copy of the
  official PDF to `~/.config/asd-ste100/config.yml`, from bookmarks only.
  SKILL.md "Lexical checks in this install" uses it for one-word lookups. No
  text of the standard is stored, because ASD does not permit reproduction
  without written authority.

To update: diff a fresh clone against this directory, keep the local changes,
and run `python3 scripts/ste-lint.py --selftest`.
