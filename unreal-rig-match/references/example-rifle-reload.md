# Worked example: rifle hold and reloads from a first person arms rig (UE 5.8)

Body: UE5 mannequin (`SKM_Manny_Simple`). Reference: a first person arms rig and a rifle in one skeleton (glb),
clips Idle, Reload_Tactical, Reload_Empty. Rig bones: `Arm_Upper_S`, `Arm_Lower_S`, `Wrist_S`, fingers
`<Finger>_01..04_S` (thumb 01..03), prop bone `<Rifle>_Body`.

## Data

- Hand size (cm), rig vs body: wrist → middle knuckle 5.14 vs 9.52; knuckle span 5.26–5.44 vs 7.02. Finger segment
  lengths are close (index 5.12/2.92/1.98 vs 4.08/2.60; middle 4.70/3.39/2.35 vs 5.17/2.47).
- Reload step times measured from the rig: magazine out 0.48 s, pouch 0.97 s, in 1.97 s, bolt 3.0 s.

## Results (lab sweep, tactical reload, 32 samples)

After the reach fit (hand shifted 1.4 cm forward): index, middle, ring and pinky tips ≤ 0.11 cm mean (max 0.41 cm),
thumbs 2.5–2.7 cm mean, left hand vs IK goal 0.02 cm mean. The hand wraps the pistol grip. Before the fit:

| Check | Mean | Max |
| --- | --- | --- |
| Left hand vs rig target (IK) | 0.03 cm | 0.83 cm |
| Right hand vs rig wrist (fixed grip, by design) | 1.71 cm | 2.57 cm |
| Middle, ring, right pinky tips | 0.00–0.10 cm | 0.97 cm |
| Left pinky tip | 0.67 cm | 1.69 cm |
| Index tips (out of reach) | 1.30–1.45 cm | 1.96 cm |
| Thumb tips (out of reach) | 3.7–4.1 cm | 4.8 cm |

Thumb cause: the body `thumb_01_r` is 5.4 cm behind the rig `Thumb_01_R`; the rig tip is 13.5 cm from it and the
body thumb is 10.1 cm long.

## What went wrong first

- Fingers "away from the rig" with correct rotations: the palm size, not the rotation (fixed by reach).
- Left elbow glued to the body on the magazine throw: a fixed downward pole (fixed by the rig elbow side).
- A false 26–45 cm hand error: a shot taken one frame after the next command changed the pose (lab timing).
- Out-of-reach fingers bent backwards: the bend search started past straight (search from the longest angle).
- The index stayed 1.4 cm short of the trigger after the knuckle-frame alignment: fixed by the reach fit.
