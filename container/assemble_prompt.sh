#!/usr/bin/env bash
# container/assemble_prompt.sh
# Assembles the exercise prompt from .docs/ + addendum.
# Usage: assemble_prompt.sh <exercise_dir> <output_file> <addendum_file>
set -euo pipefail

EXERCISE_DIR="$1"
OUTPUT_FILE="$2"
ADDENDUM_FILE="${3:-/dev/null}"

DOCS_DIR="$EXERCISE_DIR/.docs"

{
    if [ -f "$DOCS_DIR/introduction.md" ]; then
        cat "$DOCS_DIR/introduction.md"
        echo ""
    fi

    cat "$DOCS_DIR/instructions.md"
    echo ""

    if [ -f "$DOCS_DIR/instructions.append.md" ]; then
        cat "$DOCS_DIR/instructions.append.md"
        echo ""
    fi

    cat "$ADDENDUM_FILE"
} > "$OUTPUT_FILE"
