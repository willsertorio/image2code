#!/usr/bin/env python3
"""Generate the five scenes with Gemini 4 Carbon, then have Carbon grade them.

Run from the repo root, with your key in the environment (never committed):

    export OPENROUTER_API_KEY=...
    python3 rubrics/carbon.py generate            # all five samples
    python3 rubrics/carbon.py generate toast      # just one
    python3 rubrics/carbon.py followup toast      # second turn asking for the HTML, after a refusal
    python3 rubrics/carbon.py grade --runs 5      # 5 independent grading runs per sample

generate writes   rubrics/samples/<id>/model.html           the scene
                  rubrics/samples/<id>/model_response.json  the raw reply (earlier tries kept as _attemptN)
grade    writes   rubrics/samples/<id>/grades/runN.json     every raw reply
                  rubrics/carbon_runs.json                  verdicts per sample and run

grade sends Carbon the reference photo, the captures in rubrics/captures/<id>/ (the running
scene from several angles) and the scene's HTML, plus the rubric. It never sees the human scores.
Standard library only, no installs needed.
"""
import base64
import glob
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

MODEL = "google/gemini-4-carbon"
URL = "https://openrouter.ai/api/v1/chat/completions"
HERE = os.path.dirname(os.path.abspath(__file__))
RUBRICS = json.load(open(os.path.join(HERE, "rubrics.json")))
PROMPT = RUBRICS["prompt"]
SAMPLES = {s["id"]: s for s in RUBRICS["samples"]}

GRADER = """You are reviewing a real-time 3D scene. A model was given the reference photo below and the
prompt "{prompt}", and answered with the HTML page below. Score that page against the rubric.

You receive:
1. The reference photo.
2. Five screenshots of the page running in Chrome, in this order:
   1 default view, as the page opens, before any input
   2 orbited about 90° to the left
   3 orbited about 90° to the right
   4 from above
   5 zoomed all the way out
3. The page's full HTML source.

How to judge
- Judge what a visitor sees and experiences, not what the code intends. A comment or variable
  name such as "photorealistic snow" is not evidence of photorealistic snow.
- Use the screenshots for anything visual: shapes, colours, materials, lighting, framing,
  edges, clipping, on-screen UI.
- Use the code only for what screenshots can't show: motion, camera limits, frame rate, and
  what happens beyond the captured angles. Name the part of the code you relied on.
- When a criterion refers to the photo, compare with the reference photo.
- Pass a criterion only when the evidence clearly meets all of it. If it is partly met, or the
  evidence is missing or unclear, fail it.
- Score each criterion on its own. A failed gate does not affect the other criteria.
- Frame rate (G3): estimate from the scene's load (geometry, draw calls, shadow maps,
  post-processing) on a typical laptop with integrated graphics. The screenshots were rendered
  in software, so they say nothing about speed.

Output
Reply with one JSON object and nothing else:
{{"results": [{{"n": "<criterion id>", "evidence": "<what you saw or read, citing screenshot numbers or code>", "pass": true or false}}]}}
Write the evidence before the verdict, in one or two sentences. Include every criterion exactly
once, in rubric order.

Rubric
{rubric}
"""

# The five screenshots, in the order the prompt lists them (the low-angle capture is not sent).
SHOTS = ["01_default_view", "02_orbit_left", "03_orbit_right", "04_from_above", "06_zoomed_out"]
# One backend for every grading call, so run-to-run differences come from the model alone.
PROVIDER = {"order": ["google-ai-studio"], "allow_fallbacks": False}
SCHEMA = {"type": "json_schema", "json_schema": {"name": "rubric_results", "strict": True, "schema": {
    "type": "object", "additionalProperties": False, "required": ["results"],
    "properties": {"results": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["n", "evidence", "pass"],
        "properties": {"n": {"type": "string"}, "evidence": {"type": "string"}, "pass": {"type": "boolean"}}}}}}}}


def data_url(path):
    mime = "image/png" if path.endswith(".png") else "image/jpeg"
    with open(path, "rb") as f:
        return f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"


def post(body, key):
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:500]
            if e.code in (429, 500, 502, 503, 504) and attempt < 3:
                print(f"  HTTP {e.code}, retrying in {10 * 2 ** attempt}s: {msg}")
                time.sleep(10 * 2 ** attempt)
                continue
            sys.exit(f"  HTTP {e.code}: {msg}")
        except urllib.error.URLError as e:
            if attempt < 3:
                print(f"  network error, retrying: {e}")
                time.sleep(10 * 2 ** attempt)
                continue
            raise


def save_response(path, resp):
    if os.path.exists(path):  # keep earlier attempts as a record
        n = 1
        while os.path.exists(path.replace(".json", f"_attempt{n}.json")):
            n += 1
        os.rename(path, path.replace(".json", f"_attempt{n}.json"))
    with open(path, "w") as f:
        json.dump(resp, f, indent=1)
    served = resp.get("model", "?")
    if served != MODEL:
        print(f"  WARNING: OpenRouter served {served!r}, not {MODEL!r}")
    return resp["choices"][0]["message"].get("content") or ""


def extract_html(text):
    fences = re.findall(r"```(?:html|HTML)?\s*\n(.*?)```", text, re.S)
    full = [f for f in fences if "<html" in f.lower() or "<!doctype" in f.lower()]
    if full:
        return max(full, key=len).strip() + "\n"
    m = re.search(r"(<!DOCTYPE html.*?</html>)", text, re.S | re.I) or re.search(r"(<html.*?</html>)", text, re.S | re.I)
    return m.group(1).strip() + "\n" if m else None


def generate(sid, key):
    d = os.path.join(HERE, "samples", sid)
    os.makedirs(d, exist_ok=True)
    print(f"{sid}: generating with {MODEL} ...")
    resp = post({"model": MODEL, "messages": [{"role": "user", "content": [
        {"type": "text", "text": PROMPT},
        {"type": "image_url", "image_url": {"url": data_url(os.path.join(HERE, "img", f"{sid}.jpg"))}}]}]}, key)
    html = extract_html(save_response(os.path.join(d, "model_response.json"), resp))
    if not html:
        print(f"  No HTML in the reply (see {d}/model_response.json). Run it again for this sample.")
        return
    with open(os.path.join(d, "model.html"), "w") as f:
        f.write(html)
    print(f"  wrote model.html ({len(html):,} bytes, served by {resp.get('model')})")


FOLLOWUP = "Please build the scene as a single HTML file using three.js."


def followup(sid, key):
    """Second turn: replay the prompt and Carbon's latest reply, then ask for the HTML once."""
    d = os.path.join(HERE, "samples", sid)
    first = json.load(open(os.path.join(d, "model_response.json")))["choices"][0]["message"]["content"]
    print(f"{sid}: follow-up turn with {MODEL} ...")
    resp = post({"model": MODEL, "messages": [
        {"role": "user", "content": [
            {"type": "text", "text": PROMPT},
            {"type": "image_url", "image_url": {"url": data_url(os.path.join(HERE, "img", f"{sid}.jpg"))}}]},
        {"role": "assistant", "content": first},
        {"role": "user", "content": FOLLOWUP}]}, key)
    path = os.path.join(d, "followup_response.json")
    html = extract_html(save_response(path, resp))
    if not html:
        print(f"  No HTML in the follow-up reply either (see {path}).")
        return
    with open(os.path.join(d, "model.html"), "w") as f:
        f.write(html)
    print(f"  wrote model.html ({len(html):,} bytes, served by {resp.get('model')})")


def grade_once(sid, key, run):
    """One independent grading call (no shared history). Returns {criterion: {pass, evidence}} or None."""
    d = os.path.join(HERE, "samples", sid)
    caps = [os.path.join(HERE, "captures", sid, f"{n}.jpg") for n in SHOTS]
    missing = [c for c in caps if not os.path.exists(c)]
    if missing or not os.path.exists(os.path.join(d, "model.html")):
        print(f"{sid} run {run}: missing scene or captures, skipped")
        return None
    crit = SAMPLES[sid]["criteria"]
    rubric = "\n".join(f'{c["n"]} [{c["d"]}]: {c["c"]}' for c in crit)
    content = [{"type": "text", "text": GRADER.format(prompt=PROMPT, rubric=rubric)},
               {"type": "image_url", "image_url": {"url": data_url(os.path.join(HERE, "img", f"{sid}.jpg"))}}]
    content += [{"type": "image_url", "image_url": {"url": data_url(c)}} for c in caps]
    content.append({"type": "text", "text": "HTML source of the page:\n\n" + open(os.path.join(d, "model.html")).read()})
    out_dir = os.path.join(d, "grades")
    os.makedirs(out_dir, exist_ok=True)
    for attempt in range(1, 4):  # a reply we can't read is not a verdict, so it is retried
        try:
            resp = post({"model": MODEL, "temperature": 0, "provider": PROVIDER, "response_format": SCHEMA,
                         "messages": [{"role": "user", "content": content}]}, key)
        except SystemExit as e:  # an HTTP error skips this run only; rerunning the command fills it in
            print(f"  {sid} run {run}: request failed ({e}), skipped")
            return None
        name = f"run{run}.json" if attempt == 1 else f"run{run}_retry{attempt - 1}.json"
        with open(os.path.join(out_dir, name), "w") as f:
            json.dump(resp, f, indent=1)
        served, prov = resp.get("model"), resp.get("provider")
        if served != MODEL:
            print(f"  WARNING {sid} run {run}: served {served!r}")
        reply = resp["choices"][0]["message"].get("content") or ""
        m = re.search(r"\{.*\}", reply, re.S)
        try:
            got = {str(r["n"]): r for r in json.loads(m.group(0))["results"]}
        except (AttributeError, ValueError, KeyError, TypeError):
            print(f"  {sid} run {run}: unreadable reply (attempt {attempt}), retrying")
            continue
        if any(c["n"] not in got for c in crit):
            print(f"  {sid} run {run}: missing criteria (attempt {attempt}), retrying")
            continue
        res = {c["n"]: {"pass": bool(got[c["n"]]["pass"]), "evidence": str(got[c["n"]].get("evidence", "")).strip()} for c in crit}
        print(f"{sid} run {run}: {sum(v['pass'] for v in res.values())} / {len(crit)} pass ({prov})")
        return {"provider": prov, "results": res}
    return None


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("generate", "followup", "grade"):
        sys.exit(__doc__)
    key = os.environ.get("OPENROUTER_API_KEY") or sys.exit("Set OPENROUTER_API_KEY first.")
    ids = sys.argv[2:]
    for s in [x for x in ids if not x.startswith("--") and not x.isdigit()] or list(SAMPLES):
        if s not in SAMPLES:
            sys.exit(f"Unknown sample {s!r}; choose from {list(SAMPLES)}")
    if sys.argv[1] in ("generate", "followup"):
        for s in ids or list(SAMPLES):
            (generate if sys.argv[1] == "generate" else followup)(s, key)
        return
    runs = 1
    if "--runs" in ids:
        i = ids.index("--runs"); runs = int(ids[i + 1]); ids = ids[:i] + ids[i + 2:]
    ids = ids or list(SAMPLES)
    path = os.path.join(HERE, "carbon_runs.json")
    store = json.load(open(path)) if os.path.exists(path) else {}
    jobs = [(s, r) for s in ids for r in range(1, runs + 1) if str(r) not in store.get(s, {})]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=5) as pool:
        for (s, r), res in zip(jobs, pool.map(lambda j: grade_once(j[0], key, j[1]), jobs)):
            if res:
                store.setdefault(s, {})[str(r)] = res
    with open(path, "w") as f:
        json.dump(store, f, indent=1, ensure_ascii=False)
    done = {s: len(v) for s, v in store.items()}
    print(f"saved {path}: runs per sample {done}")


if __name__ == "__main__":
    main()
