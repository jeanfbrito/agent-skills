#!/usr/bin/env python3
"""Pure checks for lab readiness, game frames and the state a probe actually measures."""
import math
import statistics


class ProbeGuard:
    def __init__(self):
        self.actor = None
        self.game_time = None
        self.started = False
        self.physics = None
        self.view = None
        self.motion_min = None
        self.moved = False

    def sample(self, game_time, actor, alive, ready, physics=None, view=None, speed=0.0):
        if not math.isfinite(game_time) or not math.isfinite(speed):
            raise RuntimeError("The probe state has a non-finite value.")
        if self.started and (actor != self.actor or not alive):
            raise RuntimeError("The measured pawn changed or died. Start a new probe.")
        if not actor or not alive:
            return False
        if not ready:
            if self.started:
                raise RuntimeError("The lab lost startup readiness during the probe.")
            return False
        if not self.started:
            self.actor, self.started = actor, True
        if self.game_time is not None and game_time < self.game_time:
            raise RuntimeError("The game clock moved backward. Start a new probe.")
        if self.physics is not None and physics != self.physics:
            raise RuntimeError("The physical-arm mode differs from the required mode.")
        if self.view is not None and view != self.view:
            raise RuntimeError("The current view differs from the required view.")
        if self.motion_min is not None and speed >= self.motion_min:
            self.moved = True
        if game_time == self.game_time:
            return False
        self.game_time = game_time
        return True

    def finish(self):
        if not self.started:
            raise RuntimeError("The lab did not complete startup.")
        if self.motion_min is not None and not self.moved:
            raise RuntimeError("The measured pawn did not move at the required speed.")


def check_firing(times, interval, tolerance, rounds_before, rounds_after, physical_shots):
    """Call after chamber events finish. This does not count projectiles by itself."""
    if len(times) < 2 or interval <= 0 or tolerance < 0:
        raise ValueError("Supply at least two shot times and valid interval limits.")
    if not all(math.isfinite(value) for value in [*times, interval, tolerance]):
        raise ValueError("Firing values must be finite.")
    gaps = [b - a for a, b in zip(times, times[1:])]
    if min(gaps) <= 0:
        raise RuntimeError("Shot times must increase without duplicate samples.")
    if rounds_before - rounds_after != physical_shots or physical_shots != len(times):
        raise RuntimeError("Shot times, consumed rounds and physical shots disagree.")
    mean = statistics.mean(gaps)
    if abs(mean - interval) > tolerance:
        raise RuntimeError("The measured mean shot interval exceeds its tolerance.")
    return {"shots": len(times), "mean_interval": mean, "range": [min(gaps), max(gaps)]}
