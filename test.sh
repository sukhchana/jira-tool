#!/bin/bash
# Test multiple epics
# 

EPICS=("DP-7")

for epic in "${EPICS[@]}"; do
    echo "Testing breakdown for epic: $epic"
    curl -X POST "http://localhost:8000/api/v1/llm/create-epic-subtasks/$epic?dry_run=true" \
        -H "Content-Type: application/json" | jq '.'
    echo "----------------------------------------"
done
