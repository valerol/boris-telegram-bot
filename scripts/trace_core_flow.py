from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core_manager.core_flow_trace import trace_core_information_flow


def main() -> None:
    parser = argparse.ArgumentParser(description="Trace native BOIS Core information flow through BORIS runtime.")
    parser.add_argument("text", help="User text to trace")
    parser.add_argument(
        "--llm-output",
        default=None,
        help="Optional raw LLM output sample. If omitted, the LLM is not called.",
    )
    args = parser.parse_args()

    if args.llm_output is None:
        trace = trace_core_information_flow(args.text)
    else:
        trace = trace_core_information_flow(args.text, llm_output=args.llm_output)
    print(json.dumps(trace, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
