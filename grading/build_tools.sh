#!/usr/bin/env bash
# Build the six blind grading tools for the pilot from grading/pilot.json.
#   bash grading/build_tools.sh [rater]
set -euo pipefail
cd "$(dirname "$0")/.."
RATER="${1:-zachary}"
P=.venv/bin/python
read -r -a KEYS <<< "$($P -c "import json; print(' '.join(r['key'] for r in json.load(open('grading/pilot.json'))['items']))")"
SEED=$($P -c "import json; print(json.load(open('grading/pilot.json'))['seed'])")
mkdir -p grading/tools
declare -A LABELS=([D1]="0 1" [D2]="0 1 2" [D3]="0 1 2" [D4]="0 1 2 NA" [D5]="0 1 2 NA" [D6]="0 1 2")
declare -A TITLES=([D1]="Task success" [D2]="Tool-call correctness" [D3]="Unnecessary calls"
                   [D4]="Irreversible moves without checking" [D5]="Recovery after an injected failure" [D6]="Tool grounding")
for d in D1 D2 D3 D4 D5 D6; do
  $P -m trade_desk.judge items --dimension "$d" --keys "${KEYS[@]}" --out "grading/tools/items-$d.jsonl" | head -1
  # shellcheck disable=SC2086
  .venv/bin/motherlode handpick --items "grading/tools/items-$d.jsonl" --rubric rubric/RUBRIC.md \
    --out "grading/tools/grade-$d.html" --labels ${LABELS[$d]} --context packet --hidden judge \
    --rater "$RATER" --seed "$SEED" --title "Trade desk pilot $d: ${TITLES[$d]}" >/dev/null
done
ls -la grading/tools/grade-*.html | awk '{print $5, $9}'
