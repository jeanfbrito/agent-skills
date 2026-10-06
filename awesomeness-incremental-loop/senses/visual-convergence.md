# Sense guide: visual convergence (capture and score)

1. **Shot list.** Name each view that a reference frame shows: camera, seed,
   time or frame, state, size. Store the shot list in the project.
2. **Measurement view.** For masks and sizes, render a second capture in
   flat colours: each part has one unshaded colour, and frames are lossless.
   Thresholds on normal lighting do not transfer between scenes.
3. **Critic mode.** Turn off all gizmos. Hide everything that the check does
   not measure (`3d-views.md`, "Hide what is not measured"). Hide the HUD, debug overlays, cursors
   and anything that the reference does not show. Crop to the region of interest when only one part
   is under test. The critic must see only the thing under work.
4. **Metadata.** Each image has a sidecar record (`capture-metadata.md`).
   The critic gets the clean images only.
5. **Fresh frames.** Prove that each image is new. Put a frame number in the
   metadata or the file name, and make sure the numbers are in sequence. When
   the scene moves, no two images can have the same bytes. An occluded or
   paused window can write the same image again and again.
6. **Pairs.** Put the reference and ours at the same size, side by side or as
   a contact sheet. Remove the labels. Randomize the left and right order and
   record the key outside the image.
7. **Cheap score first.** A perceptual difference (for example SSIM, or a
   difference in histograms or edges) finds large regressions and ranks the
   shots by distance. Use it to choose what the critic looks at first.
8. **Critic last, only at the gate.** The blind critic runs only at the critic
   gate (`~/Github/agent-skills/awesomeness-incremental-loop/references/checks.md`).
   Steps 1 to 7 are the agent's own check. The critic gives the verdict and the
   deficit list.
   The deficits become new `below` items in the gap matrix.
