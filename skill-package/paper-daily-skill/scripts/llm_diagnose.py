from __future__ import annotations

from pathlib import Path

from src.llm import load_llm_settings, build_llm_client


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    s = load_llm_settings(root=root)
    print("provider:", s.provider)
    print("model:", s.model)
    print("base_url:", s.base_url)
    print("api_key_present:", bool(s.api_key))
    client = build_llm_client(s)
    out = client.generate("只回复OK")
    print("output_preview:", (out or "")[:120])
    print("ok:", bool(out.strip()))


if __name__ == "__main__":
    main()
