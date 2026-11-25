#!/usr/bin/env python3
"""Version 2 clinic test: 40 tasks x 2 languages x {clean, hidden instruction} x {plain, datamark} per model.

Every reply is appended to outputs_v2/runs.jsonl as soon as it arrives, and finished keys are skipped, so
the run can be stopped (Ctrl+C) and started again. Nothing is executed; the model only proposes actions.

  python3 run_v2.py                                  # the four models of version 2.1, needs the Ollama app
  python3 run_v2.py --models qwen2.5:3b --limit 4    # quick check on 4 tasks
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple

from clinic_v2.prompts import DEFENCES, SYSTEM, user_message

ROOT = Path(__file__).resolve().parent
TASKS = ROOT / "clinic_v2" / "tasks.json"
OUT = ROOT / "outputs_v2"
RUNS = OUT / "runs.jsonl"
LANGS = ("en", "ru")
TEMPERATURE = 0
SEED = 42
MAX_TOKENS = 256

Key = Tuple[str, str, str, str, bool]
AskFn = Callable[[str, str, str], str]


def load_tasks(path: Path = TASKS) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def grid(models: List[str], tasks: List[Dict[str, Any]]) -> Iterator[Tuple[Key, Dict[str, Any]]]:
    """Model by model, so a stopped run leaves one model complete before the next starts."""
    for model in models:
        for task in tasks:
            for lang in LANGS:
                for defence in DEFENCES:
                    for injected in (False, True):
                        yield (model, task["id"], lang, defence, injected), task


def key_of(row: Dict[str, Any]) -> Key:
    return (row["model"], row["task"], row["lang"], row["defence"], bool(row["injected"]))


def done_keys(path: Path) -> Set[Key]:
    keys: Set[Key] = set()
    if path.exists():
        for line in path.open(encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    keys.add(key_of(json.loads(line)))
                except (ValueError, KeyError):
                    continue  # a half-written last line after a crash is ignored and redone
    return keys


def _post(url: str, payload: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def ollama_ask(host: str, timeout: int = 180) -> AskFn:
    def ask(model: str, system: str, user: str) -> str:
        body = _post(host + "/api/chat", {
            "model": model, "stream": False, "format": "json",
            "options": {"temperature": TEMPERATURE, "seed": SEED, "num_predict": MAX_TOKENS},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }, timeout)
        return body.get("message", {}).get("content", "")
    return ask


def ask_with_retry(ask: AskFn, model: str, system: str, user: str) -> Tuple[str, Optional[str]]:
    """One retry on a timeout or connection error; after that the call is recorded as failed."""
    error: Optional[str] = None
    for _ in range(2):
        try:
            return ask(model, system, user), None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            error = "{}: {}".format(type(e).__name__, e)
    return "", error


def check_ollama(host: str, models: List[str]) -> Dict[str, Any]:
    try:
        version = json.loads(urllib.request.urlopen(host + "/api/version", timeout=10).read()).get("version")
        tags = json.loads(urllib.request.urlopen(host + "/api/tags", timeout=10).read()).get("models", [])
    except urllib.error.URLError as e:
        raise SystemExit("Ollama is not reachable at {} ({}). Start the Ollama app and try again.".format(host, e))
    digests = {m.get("name"): m.get("digest") for m in tags}
    missing = [m for m in models if m not in digests]
    if missing:
        raise SystemExit("Pull these models first: " + "; ".join("ollama pull " + m for m in missing))
    return {"ollama_version": version, "models": {m: digests[m] for m in models}}


def run(models: List[str], tasks: List[Dict[str, Any]], ask: AskFn, runs_path: Path = RUNS) -> int:
    runs_path.parent.mkdir(parents=True, exist_ok=True)
    finished = done_keys(runs_path)
    todo = [(k, t) for k, t in grid(models, tasks) if k not in finished]
    total = len(finished) + len(todo)
    print("{} calls in the grid, {} already done, {} to run.".format(total, len(finished), len(todo)), flush=True)
    t0 = time.time()
    with runs_path.open("a", encoding="utf-8") as f:
        for i, (key, task) in enumerate(todo, 1):
            model, task_id, lang, defence, injected = key
            s = time.time()
            reply, error = ask_with_retry(ask, model, SYSTEM[defence], user_message(task, lang, injected, defence))
            row = {"model": model, "task": task_id, "lang": lang, "defence": defence, "injected": injected,
                   "reply": reply, "error": error, "seconds": round(time.time() - s, 2)}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            if i % 10 == 0 or i == len(todo):
                rate = (time.time() - t0) / i
                print("[{}/{}] {} {} {} {} {} | ETA {:.0f} min".format(
                    len(finished) + i, total, model, task_id, lang, defence, "injected" if injected else "clean",
                    rate * (len(todo) - i) / 60), flush=True)
    return len(todo)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["qwen2.5:3b", "llama3.1:8b", "mistral:7b", "qwen2.5:7b"])
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--limit", type=int, default=0, help="use only the first N tasks (quick check)")
    a = ap.parse_args()
    data = load_tasks()
    tasks = data["tasks"][: a.limit] if a.limit else data["tasks"]
    meta = check_ollama(a.host, a.models)
    meta.update({"temperature": TEMPERATURE, "seed": SEED, "num_predict": MAX_TOKENS, "tasks": len(tasks),
                 "date": time.strftime("%Y-%m-%d"), "system_prompts": SYSTEM})
    OUT.mkdir(exist_ok=True)
    (OUT / "run_metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    run(a.models, tasks, ollama_ask(a.host))
    print("Done. Next: python3 analysis_v2.py")


if __name__ == "__main__":
    main()
