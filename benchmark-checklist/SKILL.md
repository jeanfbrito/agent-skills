---
name: benchmark-checklist
description: "Vets a performance measurement before it is reported or acted on. It covers limiter, tuning, limits, errors, repeatability, relevance, and whether the work happened. Use before reporting or acting on a measured speedup, regression, CI timing, or benchmark result. Triggered by 'benchmark', 'is this really faster', 'speedup', 'perf regression', 'CI got slower', 'vet this number', 'explain the number'."
---

# Benchmark checklist

Use this when you produce or are about to trust a performance number.
Examples: a PR's before and after, a regression claim, a CI step timing, or a
library or config choice. Answer each question below with evidence from a run, not from
a guess about the code. Adapted from
[cursor/plugins](https://github.com/cursor/plugins) `pstack`
`benchmark-checklist` and `principle-explain-the-number` (MIT License).

**Why:** A run that went wrong still prints a plausible number. Failed
requests, a cache that skipped the work, and code that never ran all produce
results that look fine. So do a side left on default settings and run-to-run
noise. If you cannot say why the number is not twice as good, you do not know what you
measured. Keep the evidence (run count, spread, limiter) with the number so a
reader can check it.

For a quick ballpark the user asked for, one run is enough. Still check
questions 4 and 7, and say it is one run. A choice between options is never a
ballpark.

## Before you run anything

- Write down the claim you expect to make, in the words you would ship
  ("export is 30% faster at p50 on the 60k-row dataset"). The questions test
  that sentence.
- Read the measurement script. Note what it times, what it counts, and what
  it ignores.
- Check load with `uptime` and the core count with `nproc` (Linux) or
  `sysctl -n hw.ncpu` (macOS). If the machine is busy, find out what is
  running. If you cannot stop it, interleave the sides so both see the same
  noise, and say so in the report.

## The questions

1. **Why not double?** Name the limiter. Profile in a run you do not report,
   because profilers and tracers slow the work down. Use these measures:
   - CPU per process (`top`, `pidstat` on Linux, `top -o cpu` on macOS).
   - A runtime profiler (`node --cpu-prof`, `py-spy`, `perf` on Linux,
     `sample <pid>` or `spindump` on macOS).
   - I/O wait.
   - Syscall counts (`strace -c` on Linux, `dtrace`/`dtruss` on macOS, which
     needs SIP relaxed, or `sample`).

   Map the hot spot to source. Watch the load generator too. If it saturates
   first, you measured the load generator. If a change did not move the
   number, the limiter explains why. Find it before calling the change useless.
2. **Was it tuned?** Run every side the way production runs it. Use these
   settings:
   - Release builds.
   - Production flags and env.
   - Batching and transaction settings.
   - Connection pools.
   - Caches as warm or cold as production sees them.
   - The same versions and data.

   If one side runs on defaults, you compared
   configurations, not implementations. A limiter that is a setting (a commit
   per row, a debug build, a missing index) means that side is untuned. Tune
   it and measure again before picking a winner. If you cannot, do not pick
   one from that run. Narrowing the claim to today's code does not fix this
   when the user is choosing what to adopt.
3. **Did it break limits?** Do the arithmetic. Compare bytes per second with
   disk and network bandwidth, and operations per second times cost per
   operation with the cores you have. Compare the time saved with the time
   the changed piece took. Removing a piece that takes 10% of the run can make
   the run at most about 11% faster. A result past a limit means the run
   measured something other than the work (a cache, a no-op, a bug).
4. **Did it error?** Count failures and non-success responses, and check the
   outputs are correct, not just present. Rejections are often fast.
   Timeouts and retries are slow. If the script does not count errors, add
   the count.
5. **Does it reproduce?** Run each side at least 5 times, alternating sides
   (A, B, A, B, ...). This stops warmup, lazy initialization, caches, and drift
   from favoring one side. Report the median and the range. A gap smaller than the
   run-to-run variation is no measurable difference. When the call is close,
   use a rank-sum test or the harness's own statistics.
6. **Does it matter?** Next to any micro result, measure the end-to-end path
   a user waits on, with realistic data sizes and concurrency. Report the
   micro result as a share of the whole. A helper that takes 1% of a request
   can make the request at most 1% faster.
7. **Did it even happen?** Check that the work ran inside the timed region.
   For example, the request reached the server, the rows were written, the
   bytes were read, and the code used the result. Lazy code (generators nobody iterates, promises
   nobody awaits, results the JIT can discard) and timeouts all produce
   numbers for work that never happened.

CI timings: per-step times from the run itself (`gh run view <id> --json
jobs`), compared across several runs, not one. Runner type, cache hit or
miss, and suite growth are the usual causes. Check them before blaming the
change.

## Report

- Lead with the verdict: faster, slower, no measurable difference, or
  inconclusive.
- Give the number with its unit, the run count, the range, and the limiter.
  For example, "p50 41 ms -> 33 ms, median of 7 runs per side. Range 32 to
  35 ms after, bound by JSON parsing on one core."
- Call the verdict inconclusive in any of these cases:
  - You claim a difference but cannot name the limiter.
  - A side ran untuned.
  - You could not check questions 4 and 7.

  Name the gap.
- Keep a PR body to one primary number. Put the runs, the range, and the
  limiter evidence in a linked artifact or notes file.
- You skipped this skill in either of these cases:
  - The evidence behind a number has no run count, no spread, or no named
    limiter.
  - The time saved is larger than the time the changed piece took.
