from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Callable

MAX_TOKENS = 4_000
TEMPERATURE = 0
TIMEOUT_SECONDS = 300


def house_base(endpoint: str | None = None) -> str:
    base = (endpoint or os.environ["MODEL_ENDPOINT"]).rstrip("/")
    return base if base.endswith("/v1") else base + "/v1"


def house_token(token: str | None = None) -> str:
    token = token or os.environ.get("MODEL_TOKEN") or os.environ.get("MODEL_API_KEY")
    if not token:
        raise SystemExit("neither MODEL_TOKEN nor MODEL_API_KEY is set")
    return token


def build_ask(model: str | None = None, *, endpoint: str | None = None, token: str | None = None,
              max_tokens: int = MAX_TOKENS, temperature: float = TEMPERATURE,
              timeout: float = TIMEOUT_SECONDS, template_kwargs: dict | None = None,
              record_dir: Path | None = None) -> Callable[[str, str], tuple[str, dict]]:
    from openai import OpenAI

    client = OpenAI(base_url=house_base(endpoint), api_key=house_token(token),
                    max_retries=0,
                    timeout=timeout)
    name = model or os.environ["MODEL_NAME"]
    switches = {"extra_body": {"chat_template_kwargs": template_kwargs}} if template_kwargs else {}
    sent = 0

    def ask(system: str, user: str) -> tuple[str, dict]:
        nonlocal sent
        started = time.time()
        reply = client.chat.completions.create(
            model=name, temperature=temperature, max_tokens=max_tokens,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}], **switches)
        sent += 1
        choice = reply.choices[0]
        text = choice.message.content or ""
        extra = getattr(choice.message, "model_extra", None) or {}
        reasoning = getattr(choice.message, "reasoning_content", None) or extra.get("reasoning_content") or ""
        usage = {"reasoning_chars": len(reasoning),
                 "tokens_in": getattr(reply.usage, "prompt_tokens", 0),
                 "tokens_out": getattr(reply.usage, "completion_tokens", 0),
                 "finish_reason": choice.finish_reason,
                 "seconds": round(time.time() - started, 2)}
        if record_dir is not None:
            record_dir.mkdir(parents=True, exist_ok=True)
            (record_dir / f"call_{sent:02d}.json").write_text(json.dumps(
                {"model": name, "max_tokens": max_tokens, "temperature": temperature, "template_kwargs": template_kwargs,
                 "system": system, "user": user, "reasoning": reasoning, "reply": text,
                 "usage": usage}, indent=2))
        return text, usage

    ask.client = client
    return ask
