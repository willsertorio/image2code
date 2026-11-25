#!/usr/bin/env python3
"""Generate the five scenes with Gemini 4 Carbon, then have Carbon grade them.

Run from the repo root, with your key in the environment (never committed):

    export OPENROUTER_API_KEY=...
    python3 rubrics/carbon.py generate            # all five samples
    python3 rubrics/carbon.py generate toast      # just one
    python3 rubrics/carbon.py followup toast      # second turn asking for the HTML, after a refusal
    python3 rubrics/carbon.py grade               # after the captures are in

generate writes   rubrics/samples/<id>/model.html           the scene
                  rubrics/samples/<id>/model_response.json  the raw reply (earlier tries kept as _attemptN)
grade    writes   rubrics/samples/<id>/carbon_grade.json    the raw reply
                  rubrics/carbon.json                       verdicts for every sample graded so far

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

GRADER = """You are reviewing a 3D scene that a model built from a reference photo, given the prompt
"{prompt}". The first image is the reference photo. The other images are captures of the running
scene: {captures}. The scene's full HTML source follows the images.

Score every rubric criterion below as pass or fail, judging what the captures and the code show.
For criteria the captures can't show (frame rate, motion, what happens when orbiting further), judge
from the code. Be strict: pass a criterion only when the scene clearly meets it.

Reply with JSON only, no other text, in this shape:
{{"results": [{{"n": "G1", "pass": true, "comment": "One or two plain sentences on why."}}, ...]}}
Include every criterion exactly once, using its id.

Rubric:
{rubric}
"""


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


def grade(sid, key):
    d = os.path.join(HERE, "samples", sid)
    caps = sorted(glob.glob(os.path.join(HERE, "captures", sid, "*.jpg")))
    if not os.path.exists(os.path.join(d, "model.html")):
        print(f"{sid}: no model.html yet, skipped")
        return None
    if not caps:
        print(f"{sid}: no captures in rubrics/captures/{sid}/ yet, skipped")
        return None
    names = ", ".join(os.path.splitext(os.path.basename(c))[0].split("_", 1)[-1].replace("_", " ") for c in caps)
    crit = SAMPLES[sid]["criteria"]
    rubric = "\n".join(f'{c["n"]} [{c["d"]}]: {c["c"]}' for c in crit)
    text = GRADER.format(prompt=PROMPT, captures=names, rubric=rubric)
    content = [{"type": "text", "text": text},
               {"type": "image_url", "image_url": {"url": data_url(os.path.join(HERE, "img", f"{sid}.jpg"))}}]
    content += [{"type": "image_url", "image_url": {"url": data_url(c)}} for c in caps]
    content.append({"type": "text", "text": "HTML source of the scene:\n\n" + open(os.path.join(d, "model.html")).read()})
    print(f"{sid}: grading {len(crit)} criteria with {MODEL} ({len(caps)} captures) ...")
    resp = post({"model": MODEL, "temperature": 0, "messages": [{"role": "user", "content": content}]}, key)
    reply = save_response(os.path.join(d, "carbon_grade.json"), resp)
    m = re.search(r"\{.*\}", reply, re.S)
    try:
        results = json.loads(m.group(0))["results"]
    except (AttributeError, ValueError, KeyError):
        print(f"  Could not read JSON from the reply (see {d}/carbon_grade.json). Run grade again for this sample.")
        return None
    got = {str(r["n"]): r for r in results}
    missing = [c["n"] for c in crit if c["n"] not in got]
    if missing:
        print(f"  Missing verdicts for {missing}. Run grade again for this sample.")
        return None
    out = {c["n"]: {"pass": bool(got[c["n"]]["pass"]), "comment": str(got[c["n"]].get("comment", "")).strip()} for c in crit}
    print(f"  {sum(v['pass'] for v in out.values())} / {len(crit)} pass")
    return out


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("generate", "followup", "grade"):
        sys.exit(__doc__)
    key = os.environ.get("OPENROUTER_API_KEY") or sys.exit("Set OPENROUTER_API_KEY first.")
    ids = sys.argv[2:] or list(SAMPLES)
    for s in ids:
        if s not in SAMPLES:
            sys.exit(f"Unknown sample {s!r}; choose from {list(SAMPLES)}")
    if sys.argv[1] in ("generate", "followup"):
        for s in ids:
            (generate if sys.argv[1] == "generate" else followup)(s, key)
        return
    path = os.path.join(HERE, "carbon.json")
    store = json.load(open(path)) if os.path.exists(path) else {}
    for s in ids:
        res = grade(s, key)
        if res:
            store[s] = res
            with open(path, "w") as f:
                json.dump(store, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
