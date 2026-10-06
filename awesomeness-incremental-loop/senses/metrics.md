# Sense guide: metrics for motion, physics and feel

Pick the metrics that the item needs. Each metric has a limit or a reference
value, and the digest reports it per run.

| Area | Example metrics |
| --- | --- |
| Feet and contact | foot slide per contact (cm), foot height error, ground penetration |
| Smoothness | jitter (second derivative of position or rotation), pops per second, blend discontinuities |
| Response | input-to-motion latency (frames), time to reach target, overshoot, settle time |
| Physics | energy drift, penetration depth, solver iterations, sleep or wake churn |
| Weapons and recoil | peak kick, recovery time, spread over time, aim return error |
| Performance | frame time p50 and p95 against the frame-rate target, hitches over a limit, memory growth |

Write the numbers per cycle in the journal so that the trend is visible. A
metric is a gate before the critic. It is not the verdict. A clip can pass
every number and still look wrong, so a visual item always gets the critic.

## Frame rate: a target, not a maximum

Start at a low, fixed frame rate. Then performance does not add noise to the
work, and every run and capture repeats.

| Project | Target | Frame-time limit (p95) |
| --- | --- | --- |
| Slow game or simulation (strategy, puzzle, exploration, builder) | 30 fps | 33.3 ms |
| Fast game (shooter, action, racing, platformer) | 60 fps | 16.7 ms |
| App with animation or scrolling | 60 fps | 16.7 ms |

1. **Lock it.** Cap the render rate at the target in dev builds, labs and
   captures. Keep the physics and input step fixed too (see "Physics rate"),
   and measure motion metrics on that step.
2. **Features and look first.** Build and check items at the target rate.
3. **Performance is a gap only when the app misses the target.** That is,
   when the p95 frame time is over the limit on the dev machine. Then it is a normal
   gap row with its own metric.
4. **More than the target is not a goal**, unless it is a root of the project
   and a reference or a project doc says so. Examples: a competitive shooter
   at 120 fps or more, VR at 90 fps or more, a rhythm game.
5. **Capture at the target rate.** Use a higher capture rate only in a lab, to
   measure fast motion (a slow-motion check).

## Physics rate: start low, raise only on proof

Physics does not need 240 Hz to be good. A slow, fixed step is also easier to
debug. There are fewer steps to read and the logs are smaller. Each step also
shows a larger, clearer change.

1. **Start low and fixed.** Use the frame-rate target as the physics rate (30
   or 60 Hz), with the engine's default solver iterations and no substeps.
2. **Measure.** Watch the physics metrics and invariants: penetration,
   tunnelling (fast bodies through thin walls), jitter at rest, joint
   stretch, energy drift.
3. **Raise only on proof.** When a metric fails, test in a lab whether the
   step size is the cause: run the same scene at double the rate. If the
   metric passes only at the higher rate, the step is the cause. Then raise
   the rate, the substeps or the solver iterations by the smallest amount that
   passes. If the metric fails at both rates, the cause is something else.
   Do not raise the rate.
4. **Prefer a local fix.** Continuous collision on one fast body, or more
   iterations on one joint chain, costs less than a higher global rate.
5. **Write it down.** Put the physics rate, the reason for each raise, and the
   metric that proved it in the journal "Setup" section.

Write the frame-rate target in the journal "Setup" section.
