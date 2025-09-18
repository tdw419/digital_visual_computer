#!/usr/bin/env python3
#
# examples/run_simple_plan.py
#
# A simple example demonstrating the end-to-end functionality of the
# AI Runtime. This script defines a plan to read a file and summarize
# its content, then executes it using the orchestrator.

import sys
from pathlib import Path

# Add the src directory to the Python path to import the orchestrator
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from ai_runtime.orchestrator import AIRuntime

def main():
    print("--- AI Runtime Integration Example ---")

    # Instantiate the runtime. It will automatically load skills from ./skills/
    runtime = AIRuntime()

    # Define a simple plan to test the summarize skill directly.
    simple_text = "This is the first sentence. This is the second sentence. This is the third."
    plan = [
        {
            "op": "CALL",
            "args": {
                "skill": "text_summarize",
                "params": {"text": simple_text, "max_sentences": 1},
                "result_to": "summary"
            }
        },
        {
            "op": "RETURN",
            "args": {
                "value": "summary"
            }
        }
    ]

    print("\nExecuting plan...")
    result = runtime.execute_plan(plan)

    print("\n--- Plan Execution Complete ---")
    print(f"Final Result (Summary):\n{result}")

    # Verify the result
    expected_summary = "This is the first sentence."

    if result == expected_summary:
        print("\n✅ Verification successful: The summary is correct.")
    else:
        print("\n❌ Verification failed: The summary is incorrect.")
        print(f"Expected: {repr(expected_summary)}")
        print(f"Got:      {repr(result)}")


if __name__ == "__main__":
    main()
