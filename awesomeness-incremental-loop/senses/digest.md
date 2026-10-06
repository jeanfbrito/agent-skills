# Sense guide: digest scripts

A digest script turns raw output into a short answer before it reaches the
agent context.

- Decode the whole clip, not a seek into it. Measure the frames that the
  critic sees, not the engine state.
- Raw data goes to a gitignored run folder, for example
  `.localdev/senses/<run-id>/`.
- The digest prints at most about 30 lines. Put one PASS or FAIL line first.
  Then print counts, min, max, p50, p95 and the values outside the limits.
  Then print the first error with a few lines of context. Give the raw file
  path last.
- Compare against the limits or reference numbers in the gap matrix. Print the
  difference, not only the value.
- Keep the digest scripts in the project, so the next cycle can run them again.
