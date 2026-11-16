#!/usr/bin/env python3
"""Literal regressions for invalid probe state and false firing-rate passes."""
import importlib.util
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("probe_guard", Path(__file__).parents[1] / "scripts/probe_guard.py")
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)


class ProbeGuardTests(unittest.TestCase):
    def test_delayed_startup_and_duplicate_slate_callbacks(self):
        guard = subject.ProbeGuard()
        self.assertFalse(guard.sample(0.1, "pawn", True, False))
        self.assertFalse(guard.sample(0.2, "pawn", True, False))
        self.assertTrue(guard.sample(0.3, "pawn", True, True))
        self.assertFalse(guard.sample(0.3, "pawn", True, True))
        self.assertTrue(guard.sample(0.4, "pawn", True, True))

    def test_physics_reset_after_ready_fails(self):
        guard = subject.ProbeGuard()
        guard.physics = True
        self.assertTrue(guard.sample(1.0, "pawn", True, True, physics=True))
        with self.assertRaisesRegex(RuntimeError, "physical-arm mode"):
            guard.sample(1.1, "pawn", True, True, physics=False)

    def test_dead_or_replaced_measured_pawn_fails(self):
        for actor, alive in (("pawn", False), ("new pawn", True), (None, False)):
            guard = subject.ProbeGuard()
            guard.sample(1.0, "pawn", True, True)
            with self.subTest(actor=actor, alive=alive), self.assertRaisesRegex(RuntimeError, "changed or died"):
                guard.sample(1.1, actor, alive, True)

    def test_a_blocked_movement_probe_cannot_pass(self):
        guard = subject.ProbeGuard()
        guard.motion_min = 20.0
        guard.sample(1.0, "pawn", True, True, speed=0)
        guard.sample(1.1, "pawn", True, True, speed=0)
        with self.assertRaisesRegex(RuntimeError, "did not move"):
            guard.finish()
        guard.sample(1.2, "pawn", True, True, speed=21)
        guard.finish()
        self.assertTrue(guard.moved)

    def test_wrong_view_and_backward_clock_fail(self):
        guard = subject.ProbeGuard()
        guard.view = "fp"
        with self.assertRaisesRegex(RuntimeError, "required view"):
            guard.sample(1.0, "pawn", True, True, view="external")
        guard.sample(1.0, "pawn", True, True, view="fp")
        with self.assertRaisesRegex(RuntimeError, "backward"):
            guard.sample(0.9, "pawn", True, True, view="fp")

    def test_ten_shots_at_wrong_interval_fail_the_rate_claim(self):
        times = [i * 0.109 for i in range(11)]
        with self.assertRaisesRegex(RuntimeError, "mean shot interval"):
            subject.check_firing(times, .075, .008, 30, 19, 11)

    def test_frame_rounded_cadence_and_round_count(self):
        result = subject.check_firing([0, .065, .150, .215, .300], .075, .008, 30, 25, 5)
        self.assertEqual(result["shots"], 5)
        self.assertAlmostEqual(result["mean_interval"], .075)
        self.assertAlmostEqual(result["range"][0], .065)
        self.assertAlmostEqual(result["range"][1], .085)
        with self.assertRaisesRegex(RuntimeError, "disagree"):
            subject.check_firing([0, .075, .150], .075, .008, 30, 27, 0)

    def test_no_ready_state_and_nonfinite_values_fail(self):
        with self.assertRaisesRegex(RuntimeError, "did not complete startup"):
            subject.ProbeGuard().finish()
        with self.assertRaisesRegex(RuntimeError, "non-finite"):
            subject.ProbeGuard().sample(float("nan"), "pawn", True, True)


class RunnerTests(unittest.TestCase):
    def test_runner_waits_for_ready_and_real_game_frames(self):
        state = {"time": 0.0, "ready": False, "callback": None, "commands": [], "logs": [], "removed": False}
        world, pawn = object(), SimpleNamespace(is_dead=lambda: False, get_velocity=lambda: SimpleNamespace(length=lambda: 0.0))
        lab = SimpleNamespace(is_startup_ready=lambda candidate: state["ready"])

        def register(callback):
            state["callback"] = callback
            return 1

        def unregister(handle):
            state["removed"] = True

        fake = SimpleNamespace(
            UnrealEditorSubsystem=object(), AnimLabActor=object(),
            get_editor_subsystem=lambda _: SimpleNamespace(get_game_world=lambda: world),
            GameplayStatics=SimpleNamespace(get_player_pawn=lambda w, index: pawn,
                get_time_seconds=lambda w: state["time"], get_all_actors_of_class=lambda w, cls: [lab]),
            SystemLibrary=SimpleNamespace(is_valid=lambda actor: True,
                execute_console_command=lambda w, command: state["commands"].append(command)),
            register_slate_post_tick_callback=register, unregister_slate_post_tick_callback=unregister,
            log=state["logs"].append, log_error=state["logs"].append, log_warning=state["logs"].append)
        script = Path(__file__).parents[1] / "scripts/anim_lab_run.py"
        with patch.dict(sys.modules, {"unreal": fake}), patch.object(sys, "argv", [str(script), "wait 1; cam fp"]):
            runpy.run_path(str(script), run_name="__main__")
        state["callback"](0)
        self.assertEqual(state["commands"], [])
        state["ready"] = True
        state["time"] = 1.0
        state["callback"](0) # Schedule one completed-frame wait.
        for _ in range(4):
            state["callback"](0)
        self.assertEqual(state["commands"], [])
        state["time"] = 1.1
        state["callback"](0)
        self.assertEqual(state["commands"], [])
        state["time"] = 1.2
        state["callback"](0)
        self.assertEqual(state["commands"], ["AnimLab cam fp"])
        self.assertTrue(state["removed"])
        self.assertIn("ANIM_LAB_RUN: done, 2 steps", state["logs"])


if __name__ == "__main__":
    unittest.main()
