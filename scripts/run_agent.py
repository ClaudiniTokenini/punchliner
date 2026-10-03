"""Start the demo agent with a chosen pack: python scripts/run_agent.py demo-agent/hr-assistant"""

from __future__ import annotations

import os
import sys


def main() -> int:
    pack = sys.argv[1] if len(sys.argv) > 1 else "demo-agent/shop-assistant"
    os.environ["AGENT_PACK"] = pack
    # Re-exec uvicorn in-process via module for Windows-friendly env inheritance.
    from uvicorn import run

    print(f"AGENT_PACK={pack}")
    run("main:app", app_dir="demo-agent", host="127.0.0.1", port=8000, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
