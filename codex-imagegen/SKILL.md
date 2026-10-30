---
name: codex-imagegen
description: "Generates or edits raster assets through Codex, triggered by '/codex-imagegen', 'generate an image with Codex', or 'Codex image generation'."
---

# Codex Image Generation

Use this skill to request raster assets from Codex through its built-in
`image_gen` tool. Do not substitute scripted drawing or a screenshot for a
requested generated image. Use another workflow for editable SVG or code assets.

## Check prerequisites

1. Run `command -v codex` and `codex --version`.
2. Read `codex exec --help` before constructing the command. Flags can change.
3. Resolve `CODEX_HOME` from the environment, with `~/.codex` as the default.
4. Read `CODEX_HOME/skills/.system/imagegen/SKILL.md` for the installed workflow.
5. Check that Codex has authentication through `codex login status`.

If the executable, authentication, or imagegen skill is missing, report the
missing prerequisite. Do not install software or copy credentials automatically.
The built-in workflow does not require `OPENAI_API_KEY`. Access and usage limits
still depend on the account. Do not describe image generation as free.

## Prepare the request

- Choose generation or editing from the user's request.
- Specify the destination as an absolute path inside the intended workspace.
- Inspect an existing destination before writing. Keep it unless replacement
  is authorized. Use a versioned filename for a new variant.
- Preserve the requested subject, style, palette, text, composition, and alpha.
  Do not impose a language, pastel palette, or aspect ratio.
- Label each input image with its role and its position in the attachment list.
- For edits, name the target image and the properties that must stay unchanged.
  Instruct Codex to view the target before it calls the built-in editing tool.
- Read `~/Github/agent-skills/shared/tone.md` before drafting visible image text.
  Use real numbers only. Anonymize customer details. State gaps as scope,
  not failure, and do not start with a defensive explanation.
- Show newly drafted public-facing text for approval before generation.
  The user's supplied final text needs no second approval.

Use this prompt structure. Remove fields that do not apply:

```text
$imagegen
Create a raster asset with the built-in image_gen tool.
Task: <generate or edit>
Purpose: <where the asset will appear>
Subject: <requested subject>
Style and composition: <requested visual constraints>
Input images: <Image 1: role; Image 2: role>
Text, verbatim: "<approved text>"
Preserve: <edit invariants or alpha requirements>
Requested dimensions: <width and height, if specified>
Destination: <absolute workspace path>
Save the selected generated image at the destination.
Report the saved path, actual dimensions, and any unmet requirements.
If image_gen is unavailable, stop and report the error.
Do not use the API fallback or substitute scripted artwork.
```

## Execute

Use the project's workspace, not this skill's directory. Pass the prompt as
one quoted argument. Single quotes preserve the literal `$imagegen` trigger.

```bash
codex exec \
  --cd /absolute/project/path \
  --skip-git-repo-check \
  '$imagegen Create the requested asset with the built-in image_gen tool. Save it at /absolute/project/path/assets/image.png. Stop if image_gen is unavailable. Do not use the API fallback or scripted artwork.' \
  < /dev/null
```

For references or an edit target, add one `--image /absolute/input.png` per
attachment before the prompt. Keep attachment order aligned with image labels.
The installed CLI documentation defines supported inputs and limits.

Keep the caller's configured model, sandbox, and approval policy. Do not add
permission-bypass flags or impose a different sandbox mode. If a restriction
blocks the destination, report it instead of changing the policy.

Run generation in the background because it can take more than a minute.
Do not start a second generation while the first request is still running.

The built-in tool can save its initial output under
`CODEX_HOME/generated_images/`. Instruct Codex to copy the selected image into
the workspace. Do not remove the original or other sessions' images.

## Check the artifact

1. Check the command's exit status and error output.
2. Check that the destination contains a new, nonempty image file.
3. Open the saved image with the image-reading tool.
4. Check the subject, approved text, composition, references, and required alpha.
5. Measure dimensions with an available image tool. Report actual dimensions.

A successful command or a Codex message alone does not prove that the image
exists or meets the request. Do not assume exact dimensions from the prompt.
Do not resize, crop, or flatten transparency unless the user authorized it.
Use an installed image tool for authorized transformations, not macOS-only `sips`.

Report the final path, checks, and unmet requirements. Image creation does not
authorize uploads or publication. Show the final artifact before requesting
publication approval. If generation fails, report the failure before retrying.
Do not silently switch to the API workflow, which has separate credentials
and usage charges.
