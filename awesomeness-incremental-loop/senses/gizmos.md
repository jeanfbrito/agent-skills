# Sense guide: debug gizmos

For visual and creative work (games, 3D, animation, layout), gizmos are the
best way to see if things match. A gizmo draws the hidden structure on top of
the image: where things are, which way they point, and where they must be.

- **Draw what the item is about.** Examples:
  - Structure: axes and pivots, bones and joint limit cones, sockets and
    attach points, bounding boxes, colliders.
  - Motion and forces: sight lines and aim rays, contact points, centre of
    mass and support area, velocity and force arrows, motion trails.
  - Reference: a grid, a scale object, a ghost of the reference pose, or the
    reference image as an overlay.
  - UI: layout boxes, spacing guides and baselines.
- **Show the target next to the actual.** Draw the reference value and the
  current value in two fixed colours, for example green for the target and red
  for the actual. Add the error as a number label.
- **One toggle per gizmo, in a UI panel.** Give the human an in-app debug
  panel with a checkbox for each gizmo group. Use lil-gui or a small HTML panel
  in a browser app. Use a debug `CanvasLayer` with check boxes in Godot. Use a
  dev-only overlay window or menu in a desktop app. The human can then look at
  the same thing that the agent measures.
- **The same toggles in the control API.** For example
  `__agent.gizmos({bones: true, sockets: true})`. A capture names its gizmo set
  in the shot list, so each run shows the same gizmos.
- **Gizmo views are for the agent and the human.** The blind critic gets the
  clean view (critic mode, all gizmos off) for the look. It can get a gizmo
  view only for a measurement question.
- **Dev only.** Gizmos and the panel stay out of ship builds, as for every
  sense. Their state persists between runs only in dev settings.
