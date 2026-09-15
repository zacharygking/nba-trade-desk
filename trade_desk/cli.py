"""One entry point: nba-trade-desk <run|session|report|publish|results> ...

Each subcommand is the module of the same name; its own arguments follow.
"""
from __future__ import annotations

import sys

COMMANDS = {"run": "trade_desk.run", "session": "trade_desk.session", "report": "trade_desk.report",
            "publish": "trade_desk.publish", "results": "trade_desk.results"}


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help") or argv[0] not in COMMANDS:
        print("usage: nba-trade-desk <" + "|".join(COMMANDS) + "> [args]\n"
              "  run      league, tasks, scenarios, in-process agent runs\n"
              "  session  start, call, finish (an outside agent plays the general manager)\n"
              "  report   trajectory tables\n"
              "  publish  runs -> an items dataset for motherlode's gate\n"
              "  results  the write-up's tables, read back from datasets")
        sys.exit(0 if argv and argv[0] in ("-h", "--help") else 2)
    import importlib
    importlib.import_module(COMMANDS[argv[0]]).main(argv[1:])


if __name__ == "__main__":
    main()
