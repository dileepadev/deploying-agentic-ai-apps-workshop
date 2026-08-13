# Screenshots for the deck

Drop your Thursday screenshots here, then replace the matching `.shot`
placeholder in [`../../index.html`](../../index.html) with an `<img>`:

```html
<div class="shot"><img src="assets/img/504-timeout.png" alt="A 504 gateway timeout" /></div>
```

Search `index.html` for `TODO` to find every placeholder.

| Filename | Slide | What to capture |
|---|---|---|
| `demo-mid-run.png` | 4 | The UI mid-run with "Agent is searching…" visible |
| `504-timeout.png` | 8 | A real timeout from your own `/runs/naive` testing |
| `steps-and-ui.png` | 25 | Supabase `steps` rows next to the UI rendering them |
| `repo-qr.png` | 30 | QR code to the repo — test it from 5 m away |

Also worth having on hand even if they don't go on a slide: Render build logs
mid-deploy, and Render's environment-variables panel. Both are useful to show
live while a build runs.

**Keep them under ~500 KB each.** They're committed to the repo and served over
GitHub Pages.
