"""Download the Ollama models listed in config/models.yaml, then repair their manifests.

Ollama 0.40 on Windows stores each manifest as a symlink under models/manifests-v2.
With Windows Redirection Guard on, the server refuses to follow those links
("path cannot be traversed because it contains an untrusted mount point") and
lists no models. Replacing each link with a copy of its target fixes it.

Some GGUFs (Qalb, Alif) ship without a chat template, so Ollama feeds them the bare
prompt and they ramble. Config entries with `source` and `chat_format` are pulled
from `source` and re-created as `model` with the right template.

Usage: python scripts/ollama_pull.py            # pull all ollama models in the config
       python scripts/ollama_pull.py --fix-only # just repair manifests
"""

import argparse
import json
import os
import time
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OLLAMA = "http://localhost:11434"
MODELS_DIR = Path(os.environ.get("OLLAMA_MODELS", Path.home() / ".ollama/models"))

CHAT_FORMATS = {
    # Qalb model card: Llama 3 chat format, stop on <|eot_id|>, repetition penalty 1.1.
    "llama3": {
        "template": (
            "<|begin_of_text|>{{- if .System }}<|start_header_id|>system<|end_header_id|>\n\n"
            "{{ .System }}<|eot_id|>{{ end }}<|start_header_id|>user<|end_header_id|>\n\n"
            "{{ .Prompt }}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
        ),
        "parameters": {"stop": ["<|eot_id|>", "<|end_of_text|>"], "repeat_penalty": 1.1},
    },
    # Alif Training/train_ft.py: Alpaca prompt, terminated by <|end_of_text|>.
    "alpaca": {
        "template": (
            "Below is an instruction that describes a task. Write a response that "
            "appropriately completes the request.\n\n### Instruction:\n{{ .Prompt }}\n\n### Response:\n"
        ),
        "parameters": {"stop": ["<|end_of_text|>", "### Instruction:"], "repeat_penalty": 1.1},
    },
}


def pull(model: str, retries: int = 3) -> bool:
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(
            f"{OLLAMA}/api/pull", data=json.dumps({"model": model}).encode(),
            headers={"Content-Type": "application/json"},
        )
        last_status, error = None, None
        with urllib.request.urlopen(req, timeout=None) as resp:
            for line in resp:
                msg = json.loads(line)
                if "error" in msg:
                    error = msg["error"]
                    break
                status = msg.get("status", "")
                if status != last_status and not status.startswith("pulling "):
                    print(f"  {status}")
                last_status = status
        if error is None and last_status == "success":
            return True
        print(f"  attempt {attempt} failed: {error}")
        time.sleep(10)
    return False


def fix_manifests() -> int:
    fixed = 0
    for path in (MODELS_DIR / "manifests-v2").rglob("*"):
        if path.is_symlink():
            target = Path(os.readlink(path))
            if not target.is_absolute():
                target = (path.parent / target).resolve()
            if not target.exists():
                # Ollama's cleanup can delete the manifest blob it couldn't see through
                # the link. Drop the dangling link so the next pull starts clean.
                print(f"  removed dangling link {path.relative_to(MODELS_DIR)}; re-run to pull it again")
                path.unlink()
                continue
            data = target.read_bytes()
            path.unlink()
            path.write_bytes(data)
            fixed += 1
    return fixed


def create_with_template(name: str, source: str, chat_format: str) -> None:
    fmt = CHAT_FORMATS[chat_format]
    body = {"model": name, "from": source, "stream": False, **fmt}
    req = urllib.request.Request(
        f"{OLLAMA}/api/create", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        print(f"  created {name} ({chat_format} format): {json.load(resp).get('status')}")


def list_models() -> list[str]:
    with urllib.request.urlopen(f"{OLLAMA}/api/tags") as resp:
        return [m["name"] for m in json.load(resp)["models"]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix-only", action="store_true")
    args = ap.parse_args()

    if not args.fix_only:
        fix_manifests()
        installed = list_models()
        config = yaml.safe_load((ROOT / "config/models.yaml").read_text(encoding="utf-8"))
        for m in config["models"]:
            if m["backend"] == "ollama" and m.get("enabled"):
                # Re-pulling an installed model triggers Ollama's cleanup, which can
                # delete the manifest it can't see through the link.
                if m["model"] in installed or f"{m['model']}:latest" in installed:
                    print(f"== {m['name']}: already installed")
                    continue
                source = m.get("source", m["model"])
                print(f"== {m['name']} ({source})")
                if source not in installed and not pull(source):
                    print(f"  GAVE UP on {source}")
                    continue
                fix_manifests()
                if "chat_format" in m:
                    create_with_template(m["model"], source, m["chat_format"])
                    fix_manifests()

    print(f"repaired {fix_manifests()} manifest link(s)")
    print("ollama sees:", list_models())


if __name__ == "__main__":
    main()
