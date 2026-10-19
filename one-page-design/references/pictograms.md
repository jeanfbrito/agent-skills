# Pictograms

Original line drawings on a 24-unit grid. Place one above the name in
each node, scaled to about 26 units, with the figure's stroke:

```html
<g class="ico" transform="translate(CX-13,Y+4) scale(1.1)">...</g>
```

```css
svg .ico { fill: none; stroke: #1a1a1a; stroke-width: 1.3; stroke-linecap: round; stroke-linejoin: round; }
svg rect.region-box.memory { fill: #fbf7ef; }   /* warm: things in memory */
svg rect.region-box.disk   { fill: #f1f5f8; }   /* cool: things on disk  */
```

Draw a new one the same way: one `<path>` of straight runs and small
arcs, no fill, nothing under 2 units, readable at 26 units on paper.
Draw the thing the node is, not a metaphor the reader must decode.

| Thing | Path |
| --- | --- |
| a session, a terminal | `M3,4 h18 v16 h-18 z M3,8 h18 M6,12 l3,2.5 -3,2.5 M11,17 h5` |
| an agent | `M5,9 h14 v10 h-14 z M12,9 v-3 M12,6 m-1.5,0 a1.5,1.5 0 1,0 3,0 a1.5,1.5 0 1,0 -3,0 M9,14 h0.01 M15,14 h0.01 M9,17 h6` |
| a blind critic (eye, banded) | `M3,12 c3,-5 15,-5 18,0 c-3,5 -15,5 -18,0 z M2,12 h20` plus `<circle cx="12" cy="12" r="2.2"/>` |
| a door | `M6,3 h12 v18 h-12 z M6,21 l-3,-2 v-16 l3,-1 M14.5,12 m-1,0 a1,1 0 1,0 2,0 a1,1 0 1,0 -2,0` |
| a notebook, a journal | `M5,3 h14 v18 h-14 z M8,3 v18 M11,8 h5 M11,11 h5 M11,14 h5` |
| a folder of files | `M4,7 h5 l2,2 h9 v11 h-16 z M4,7 v-2 h5 l2,2 M7,13 h10 M7,16 h7` |
| a gauge, a measure | `M3,19 a9,9 0 0,1 18,0 M12,19 l5,-7 M3,19 h18` plus `<circle cx="12" cy="19" r="1.2"/>` |
| a report page with bars | `M5,3 h10 l4,4 v14 h-14 z M15,3 v4 h4 M8,17 v-4 M11,17 v-7 M14,17 v-5` |
| a person | circle head r 10, a body line, an arm line, two leg lines; see the human on the awesomeness sheet |
| a strip of notes | a tall box with one small `rect` row per note kind, labelled at 8 units |
