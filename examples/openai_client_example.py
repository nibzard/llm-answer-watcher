#!/usr/bin/env python3
"""
Example usage of OpenAIClient for LLM Answer Watcher.

This script demonstrates how to use the OpenAIClient to query OpenAI's API
with automatic retry logic and cost tracking.

Usage:
    # Set your OpenAI API key
    export OPENAI_API_KEY="sk-..."

    # Run the example
    python examples/openai_client_example.py

Note:
    This example requires the OpenAI API key to be set in the environment.
    You will be charged for API usage based on OpenAI's pricing.
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_answer_watcher.llm_runner.models import build_client
from llm_answer_watcher.llm_runner.openai_client import OpenAIClient


def main():
    """Demonstrate OpenAIClient usage."""
    # Get API key from environment
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Usage: export OPENAI_API_KEY='sk-...'")
        sys.exit(1)

    # Example 1: Direct instantiation
    print("=" * 80)
    print("Example 1: Direct OpenAIClient instantiation")
    print("=" * 80)

    client = OpenAIClient("gpt-4o-mini", api_key)
    print(f"✓ Client created for model: {client.model_name}")

    prompt = "What are the best email warmup tools for 2025?"
    print(f"\nPrompt: {prompt}")
    print("\nSending request to OpenAI...")

    try:
        response = client.generate_answer(prompt)

        print("\n✓ Response received:")
        print(f"  - Provider: {response.provider}")
        print(f"  - Model: {response.model_name}")
        print(f"  - Tokens used: {response.tokens_used}")
        print(f"  - Cost: ${response.cost_usd:.6f}")
        print(f"  - Timestamp: {response.timestamp_utc}")
        print("\nAnswer (first 200 chars):")
        print(f"  {response.answer_text[:200]}...")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)

    # Example 2: Using factory function
    print("\n" + "=" * 80)
    print("Example 2: Using build_client() factory")
    print("=" * 80)

    client2 = build_client("openai", "gpt-4o-mini", api_key)
    print("✓ Client created via factory")

    prompt2 = "What are the top CRM platforms?"
    print(f"\nPrompt: {prompt2}")
    print("\nSending request...")

    try:
        response2 = client2.generate_answer(prompt2)

        print("\n✓ Response received:")
        print(f"  - Tokens: {response2.tokens_used}")
        print(f"  - Cost: ${response2.cost_usd:.6f}")
        print("\nAnswer (first 200 chars):")
        print(f"  {response2.answer_text[:200]}...")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)

    # Example 3: Error handling
    print("\n" + "=" * 80)
    print("Example 3: Error handling demonstration")
    print("=" * 80)

    # Test empty prompt validation
    try:
        client.generate_answer("")
        print("✗ Should have raised ValueError for empty prompt")
    except ValueError as e:
        print(f"✓ Validation works: {e}")

    # Test empty model name validation
    try:
        OpenAIClient("", api_key)
        print("✗ Should have raised ValueError for empty model_name")
    except ValueError as e:
        print(f"✓ Validation works: {e}")

    # Test empty API key validation
    try:
        OpenAIClient("gpt-4o-mini", "")
        print("✗ Should have raised ValueError for empty api_key")
    except ValueError as e:
        print(f"✓ Validation works: {e}")

    print("\n" + "=" * 80)
    print("All examples completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
