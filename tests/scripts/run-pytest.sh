#!/usr/bin/env bash

set -euo pipefail

TEST_DIR="tests/e2e"
TEST_LIST="/etc/test-list/test_list.txt"

echo "--- Raw content of $TEST_LIST ---" >&2
cat "$TEST_LIST" >&2
echo "---------------------------------" >&2

# Parse tests from JSON
ACTIVE_TESTS=()
while IFS= read -r test_file; do
  ACTIVE_TESTS+=("$TEST_DIR/$test_file")
done < <(jq -r '.tests[]' "$TEST_LIST")

# Execute tests
if [ ${#ACTIVE_TESTS[@]} -gt 0 ]; then
  echo "Executing tests parsed from JSON list:"
  printf ' - %s\n' "${ACTIVE_TESTS[@]}"
  pytest -v -s "${ACTIVE_TESTS[@]}"
else
  echo "No active tests were found after processing '$TEST_LIST' with jq." >&2
  echo "This might indicate an issue with jq's parsing, an empty test list, or all tests being commented out." >&2
  exit 1
fi