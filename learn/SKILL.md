# /learn — Capture Knowledge

Trigger: `/learn`

When the user invokes `/learn`, there's something worth remembering. This covers ANY kind of learning:

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

2. **Classify and write to the appropriate locations. There are THREE levels:**
   - **Project-specific** → project memory `lessons.md`
     Things that only make sense in THIS codebase. Examples: "settings precedence: appAsar overrides userData in data.ts", "@ewsjs/xhr creates agents at xhrApi.ts:144", "use centralized outlookLog logger"
     **Test**: Would this help someone working on a DIFFERENT project with the same tech stack? If no → project.
   - **Technology-specific** → `~/.claude/lessons.md` under a section named for the technology (e.g., `## Electron`, `## Node.js`, `## React`, `## Rails`)
     Platform/framework behavior reusable across projects. Examples: "Electron has split TLS: Chromium trusts OS certs, Node.js doesn't", "`setDefaultCACertificates` beats monkey-patching `createSecureContext`"
     **Test**: Would this help someone working on a DIFFERENT project using the same technology? If yes → technology section in global.
   - **General engineering** → `~/.claude/lessons.md` under technology-agnostic sections
     Principles that apply regardless of language, framework, or platform. Examples: "test all configurations not just default", "A/B test against baseline before declaring success"
     **Test**: Does this apply even if you swap out every technology in the stack? If yes → general.

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

5. **For global `~/.claude/lessons.md`:**
   Add a concise rule under the appropriate section (create if needed):
   ```
   - **Rule title.** One-sentence explanation of what to do and why.
   ```

6. **Check for existing related entries.** Update and strengthen existing entries rather than duplicating. If a lesson keeps reappearing, the existing rule needs to be sharper.

7. **Update project MEMORY.md** if the learning changes how the project should be approached.

8. **Report** to the user: what was learned, where it was saved.

## Rules
- Be honest about mistakes — don't euphemize
- User corrections are ALWAYS right
- Focus on actionable RULES, not just stories
- Discoveries are just as valuable as bug lessons — capture both
- Keep entries concise (under 10 lines each)
- For struggles: estimate cost (user corrections x ~2min, or count failed attempts)
