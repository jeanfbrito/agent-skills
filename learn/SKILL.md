---
name: learn
description: Capture durable lessons from the current session into project and global lessons.md files, feed skill-specific lessons back into the skill itself, and spot new skills that would help with the work (repeated procedures, ad-hoc scripts, recipes outgrowing lessons.md). Use when the user types /learn, says "remember this", "capture this lesson", "add this to lessons", "write this down so we don't repeat it", "the skill should have caught this", "add this to the X skill", "the X skill missed this", "should this be a skill", "what skills could help here", or "suggest skills" — and proactively offer it after any session where the agent was corrected repeatedly, burned multiple attempts on the same problem, discovered a non-obvious behavior worth keeping, worked out a multi-step procedure it will need again, or a skill fired wrong (or should have fired and didn't).
---

# /learn — Capture Knowledge

When this skill triggers, there's something worth remembering. This covers ANY kind of learning:

**From struggles:**
- The user had to correct or guide the agent
- Something took too many iterations before success
- Going in circles before finding the right approach

**From discoveries:**
- Found how something actually works (vs how you assumed it worked)
- Discovered a non-obvious project pattern, convention, or quirk
- Learned a useful technique, tool capability, or shortcut
- Figured out why something is designed a certain way
- Found a better approach than the obvious one

**From engineering insights:**
- A general principle that applies beyond this project
- A debugging technique that worked well
- An architectural pattern worth remembering
- Performance characteristics or trade-offs discovered

Capture it NOW before the context scrolls away.

## Steps

1. **Identify what was learned.** Scan the recent conversation for:
   - User corrections or guidance
   - "Aha" moments — things that weren't obvious until discovered
   - Non-obvious project patterns or conventions
   - Failed approaches that revealed why the right approach works
   - Performance discoveries or architectural insights
   - Tool/API capabilities that weren't obvious
   - Things the user had to repeat or emphasize
   - A skill that fired (or failed to fire) and left a gap
   - Context the user pasted that a connected tool could have fetched (a Jira
     key, a Rocket.Chat thread, a PR, a log). The lesson goes to the skill
     that owns that workflow: fetch it next time
   - Work that no skill covered but will come back (see 1d)

1d. **Spot skill candidates.** Lessons are rules; a skill is a procedure.
   Look for work in this session that a skill would make faster or right
   the first time:
   - A multi-step procedure the agent worked out by trial (commands, order,
     checks) and will need again on the next ticket, repo, or release.
   - Instructions the user had to spell out step by step, or has given in
     earlier sessions (grep `lessons.md`, project memory, and handoffs).
   - An ad-hoc script or command chain that does a reusable job.
   - A `lessons.md` section that has grown into an ordered recipe: move it
     into a skill and leave a one-line pointer.
   - A connected tool or MCP used by hand each time with the same pattern.

   Keep a candidate only if it passes all of these:
   - **Repeats**: seen at least twice (this session plus one earlier piece of
     evidence). For one session alone, propose it as "watch" and do not
     build it. For cross-session evidence, offer `session-mining` ("skill
     candidates from repeated work").
   - **Not already covered**: check the installed skill list, plugin skills,
     and (for Rocket.Chat work) the rocketchat-skills catalog. If a skill
     covers it but did not fire or missed a step, it is skill feedback
     (level 4), not a new skill.
   - **More than a rule**: one sentence fits in `lessons.md`; a skill needs
     steps, a script, or a trigger worth matching.

1b. **Enforce before you write.** For each candidate, ask whether a mechanism
   can make the mistake impossible or make it fail loud. The mechanisms,
   strongest first:
   - Architecture: one owner, one way, internals unreachable.
   - A type.
   - A lint or CI check whose error names the fix.
   - A test.
   - A hook.

   If one can, the lesson is that mechanism. Propose it (or build it when the
   user asked for fixes) and record only a one-line pointer to it. Text is for
   judgment calls nothing can check.

1c. **Filter.** Drop a candidate unless it passes all of these:
   - **Durable**: still true after paths, SHAs, and versions change.
   - **Decision-changing**: a future agent acts differently because of it.
   - **Not already covered**: read the target file first. If the rule exists
     and was skipped, the fix is wording or placement that makes it fire, not
     a second copy. A rule broken twice despite being written down goes to 1b.
   - **Not a one-off**: one weird session is an anecdote.

2. **Classify and write to the appropriate locations. There are FIVE levels:**
   - **Project-specific** → project memory `lessons.md`
     Things that only make sense in THIS codebase. Examples: "settings precedence: appAsar overrides userData in data.ts", "@ewsjs/xhr creates agents at xhrApi.ts:144", "use centralized outlookLog logger"
     **Test**: Would this help someone working on a DIFFERENT project with the same tech stack? If no → project.
   - **Technology-specific** → `~/.claude/lessons.md` under a section named for the technology (e.g., `## Electron`, `## Node.js`, `## React`, `## Rails`)
     Platform/framework behavior reusable across projects. Examples: "Electron has split TLS: Chromium trusts OS certs, Node.js doesn't", "`setDefaultCACertificates` beats monkey-patching `createSecureContext`"
     **Test**: Would this help someone working on a DIFFERENT project using the same technology? If yes → technology section in global.
   - **General engineering** → `~/.claude/lessons.md` under technology-agnostic sections
     Principles that apply regardless of language, framework, or platform. Examples: "test all configurations not just default", "A/B test against baseline before declaring success"
     **Test**: Does this apply even if you swap out every technology in the stack? If yes → general.
   - **Skill-specific** → the skill's own `SKILL.md`, via `update-skill`, NOT a lessons.md
     The lesson is about one of the user's own Claude Code skills (in `~/Github/agent-skills`, symlinked into `~/.claude/skills/`), not about the codebase. Signals: a skill that should have triggered didn't (or triggered wrongly); the agent followed a skill but its instructions were missing a rule/step/edge case this session exposed; a skill's description lacked the phrase the user actually said; a skill's step produced output the user had to correct. Examples: "postmortem skill: add a step to check for an existing Confluence page before drafting", "weekly-digest: 'what did I do this week' wasn't in the trigger list"
     **Test**: Would the fix be an edit to a SKILL.md rather than a note about code/tech? If yes → skill-specific.
   - **New skill** → a proposal (step 5b), built only after approval
     A candidate from 1d. Scope: one repo → that project's `.claude/skills/`;
     any repo → `~/Github/agent-skills` via `update-skill`.
     **Test**: Is it an ordered procedure that will run again, and does no existing skill own it? If yes → new skill.

3. **For struggles/bugs — use this structure in project `lessons.md`:**
   ```
   ## <short title> (Cost: ~Xmin or ~N attempts)
   **What happened**: What went wrong or took too long
   **Root cause**: The real reason
   **What solved it**: The fix or guidance
   **Rule**: Concrete rule to prevent recurrence
   ```

4. **For discoveries/insights — use this structure in project `lessons.md`:**
   ```
   ## Discovery: <short title>
   **Context**: What led to finding this
   **Insight**: What was learned
   **Implication**: How this changes how we work
   ```

5. **For skill-specific lessons — do NOT write to lessons.md.** Use this
   structure to scope the fix, then invoke `update-skill` to apply it (it
   holds the repo conventions: README bullet sync, absolute paths, ≤200
   lines):
   ```
   ## Skill feedback: <skill-name>
   **What happened**: What the skill got wrong or missed
   **Missing**: The rule/phrase/step the skill lacked
   **Edit**: Section + exact text to add → applied via update-skill
   ```
   Show the proposed diff-in-words first; the user approves before
   `update-skill` edits anything. Never commit. If the lesson is about a
   skill NOT in the user's repo (a plugin/superpowers/built-in skill),
   fall back to a general-engineering rule in `~/.claude/lessons.md`
   noting the workaround, since those files aren't ours to edit.

5b. **For new-skill candidates — propose, do not build.** Show each one:
   ```
   ## Skill candidate: <kebab-name>  (build | watch)
   **Evidence**: where it happened — this session + earlier occurrence
   **Description**: draft frontmatter line — what, when, trigger phrases
   **Steps**: 3–7 line outline; scripts it would ship
   **Location**: project .claude/skills/ | ~/Github/agent-skills
   **Replaces**: lessons.md entries or manual steps it absorbs
   ```
   On approval, build it with `update-skill` (agent-skills) or write the
   project skill directly, reusing the commands and scripts that worked in
   this session. A "watch" candidate goes to project `lessons.md` as
   `- **Skill candidate: <name>.** <one line>` so the next /learn can count
   the second occurrence. Never commit.

6. **For global `~/.claude/lessons.md`:**
   Add a concise rule under the appropriate section (create if needed):
   ```
   - **Rule title.** One-sentence explanation of what to do and why.
   ```

7. **Check for existing related entries.** Update and strengthen existing entries rather than duplicating. If a lesson keeps reappearing, the existing rule needs to be sharper.

8. **Update project MEMORY.md** if the learning changes how the project should be approached.

9. **Report** to the user: what was learned, where it was saved, and the
   skill candidates (build / watch), or "no skill candidates" in one line.

## Rules
- Be honest about mistakes — don't euphemize
- User corrections are ALWAYS right
- Focus on actionable RULES, not just stories
- Discoveries are just as valuable as bug lessons — capture both
- Keep entries concise (under 10 lines each)
- For struggles: estimate cost (user corrections x ~2min, or count failed attempts)
- Skill lessons go into the skill, not lessons.md — a rule the agent only reads when it remembers to is weaker than a rule inside the skill that triggers
- A procedure that repeats belongs in a skill, not in a long lessons.md entry — but one session is not a pattern
</content>
