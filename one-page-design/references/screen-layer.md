# Screen layer

`~/Github/agent-skills/one-page-design/screen-layer.js` is inlined into
every sheet as the last element of `<body>`:

```html
<script>/* contents of screen-layer.js */</script>
```

Copy the file's text in. Do not link it: the sheet must open from disk
with no network and no sibling file.

The layer runs only on screen. It never changes the print. The fit check
proves this by rendering the PDF with and without the script and
comparing the pages. The only thing from the layer that prints is the
pencil marks, because the marked-up sheet is the working copy.

## Markup the layer reads

| Attribute | On | Meaning |
| --- | --- | --- |
| `data-id="x"` | an svg `<g>`, a `<path>` edge, or an aside `<p>` or `<li>` | The layer can address and highlight this element. |
| `data-rel="a b"` | a node or an edge | Ids this element touches. An edge lists both ends. |
| `data-for="x"` | a callout | The node this callout describes. Hover draws a leader line between them. |
| `data-src="path:line"` | any label, node or callout | Where the fact was read. `user` when the user said it. `unknown` for an empty callout. |

Rules:

- Every `<text>` in the figure, and every `<p>` and `<li>` in an aside,
  is inside an element with `data-src`, or carries one itself. The fit
  check fails on a label with no source.
- A `data-src` points at a real line that states the fact. Do not point
  at a file in general. The reader clicks it to check you.
- `data-rel` lists only relationships you read. The hover trace is the
  reader's test of the picture, so a wrong `data-rel` is a wrong sheet.
- Give each node a `tabindex` of 0 only if the layer does not already
  add one. The layer adds it.

## What the reader gets

- Hover or focus a node: its edges and neighbours stay, the rest dims.
  Hover a callout: its node lights and a dashed leader joins them.
- Hover a label: its source shows. Click copies it.
- Wheel or pinch over the figure: zoom toward the pointer. Drag: pan.
  Double-click or `0`: reset. The tiers of the sheet become distance.
- `P`: pencil. Strokes go into an overlay, persist in the browser for
  this file, print with the sheet, and `S` saves them as
  `<title>.marks.svg` next to the HTML. `E` erases the last stroke.
- A one-line legend sits bottom-right on screen only.

## Not in the layer

- No auto-layout, no library, no network.
- No sliders or scrubbers yet. A score, storyboard or time + space
  sheet can get a time scrubber, and a units sheet can get real
  sliders, as a later addition to this file, only when the rule behind
  them was read from the code or given by the user.
