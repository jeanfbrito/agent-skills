# Sense guide: 3D views (many angles, nothing extra in view)

## When to use it

Any check on 3D work: modelling, alignment of parts, poses, animation, physics,
cameras, lighting. Use it in the self-check, in labs, and for the critic gate.

## The blocker

- **Sign:** a part looks right in the check view, but it is wrong in depth.
  For example, a hand looks on the grip from the front, but it floats 4 cm
  behind it. Or a capture is full of the room, the HUD and other characters,
  so the agent and the critic look at the wrong thing.
- **Cause:** one camera shows only two of the three axes. Everything else in
  the frame adds noise that hides the small difference under test.

## Many angles

1. **Never trust one view for 3D.** Check each 3D item from at least two
   views at 90 degrees to each other. Use three views when position matters
   on all axes.
2. **Standard view set.** Define these as named shots in the shot list:
   - Front, side and top orthographic views, centred on the subject.
   - The real view: the gameplay or user camera, because that is what the
     human sees.
   - A close-up on the contact or the joint under test (hand on the grip, foot
     on the ground, a part in its socket).
3. **Same views every time.** Fix each camera's position, angle, size and
   projection. A change between runs must come from the subject, not from
   the camera.
4. **Read the numbers too.** Show the error per axis in a gizmo label (x, y, z
   in mm, angle in degrees). A view shows where the error is. The number shows
   how large it is.
5. **One contact sheet.** Put all views of one moment in one image, at the
   same size, with a small view name in each corner. One look then covers all
   angles. Read it at a size where the error is more than a few pixels.

## Hide what is not measured

1. **Isolate the subject.** Show only the parts that the check is about.
   Give the control API one call for this, for example
   `__agent.isolate(["hands", "grip"])`, and one call to show all again.
2. **Hide, but do not remove.** Turn off visibility with render layers, camera
   cull masks or a visible flag. Do not remove nodes or disable their logic. A
   removed part can change the behavior under test (a pose without the prop in
   the hands is a different pose).
3. **Remove the noise.** Turn these off unless the check is about them:
   - HUD, cursor, debug text and gizmos that the check does not use.
   - Environment, other characters, particles and decals.
   - Post effects: motion blur, depth of field, bloom, film grain, vignette.
   - Shadows and dynamic lights, when the check is about shape or position.
4. **Neutral background and flat light.** Use a plain mid-grey background and
   flat or fixed three-point light. For masks, use the flat-colour measurement
   view (`visual-convergence.md`).
5. **Freeze what does not move in the test.** Pause idle animations, cloth,
   camera bob and other motion that the check does not measure.
6. **Name each isolation set** in the shot list, next to its camera. The same
   shot then always hides the same things.

Examples by engine:

| Engine | Hide | Many angles |
| --- | --- | --- |
| Three.js | `object.layers` with `camera.layers`, or `object.visible` | Extra cameras with `OrthographicCamera`, rendered to one canvas with `setViewport` and `setScissor` |
| Godot | `VisualInstance3D.layers` with `Camera3D.cull_mask`, or `visible` | Extra `Camera3D` nodes in `SubViewport`s, or one camera moved to named transforms |
| Blender | Collections hidden for render, local view | Named camera objects, one render per camera |

## Proof that it works

Move the subject 1 cm along the depth axis of the real view. The real view
alone must not show it clearly, and the side or top view must show it. If no
view shows it, the views are wrong or too small. Then hide one part on
purpose and make sure the behavior under test does not change.

## Cost and limits

Each extra view costs one render. Render all views from one frame, not one
run per view. The real view still decides how the human sees it, so the
critic gate always includes it.
