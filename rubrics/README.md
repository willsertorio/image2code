# Rubrics: Gemini 4 Carbon as scene builder and judge

Five photos, each turned into a 3D scene by Gemini 4 Carbon (`google/gemini-4-carbon` on OpenRouter) from the
prompt "transform this image into a photorealistic 3D scene", then graded against a rubric by a human review and
20 times by Carbon. The page is `index.html`, live at https://willsertorio.github.io/image2code/rubrics.

## Data

| File | What it holds |
|---|---|
| `data/carbon_runs.csv` | One row per design, criterion and Carbon run (3,280 rows): pass (1/0), Carbon's evidence, the human verdict, the provider |
| `data/summary_by_criterion.csv` | One row per design and criterion (164 rows): Carbon passes out of 20, Carbon's majority, the human verdict and comment |
| `carbon_runs.json` | The same Carbon verdicts as JSON: `{design: {run: {provider, results: {criterion: {pass, evidence}}}}}` |
| `human.json` | Human verdicts and comments: `{design: {criterion: {pass, comment}}}` |
| `rubrics.json` | The prompt, the model and every criterion with its category |
| `samples/<design>/grades/runN.json` | Every raw grading reply from OpenRouter (20 per design), including token usage and cost |
| `samples/<design>/model.html` | The scene Carbon built |
| `samples/<design>/model_response*.json` | Raw generation replies; `_attemptN` files are earlier tries kept as a record |
| `samples/toast/followup_response.json` | French Toast: the follow-up turn that produced its scene |
| `captures/<design>/` | The screenshots of each scene; grading used five of them (not `05_low_angle.jpg`) |
| `img/` | The reference photos |

## How Carbon graded

Each run is a separate request with no shared history: the reference photo, five screenshots (default view,
orbit left, orbit right, from above, zoomed out), the scene's HTML and the rubric, at temperature 0, pinned to
one provider (Google AI Studio), with a JSON schema for the reply. The prompt is `GRADER` in `carbon.py`.

## Scripts

- `carbon.py generate | followup | grade --runs N`: builds the scenes and grades them through OpenRouter
  (needs `OPENROUTER_API_KEY`).
- `capture.js`: records the screenshots with Playwright.
- `build.py`: rebuilds `index.html` from the data.
