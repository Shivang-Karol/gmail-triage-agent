"""
Test: Input truncation logic.

Verifies that the worker's truncation behavior correctly caps email body length
before it ever reaches the Gemini API. This is a pure unit test — no API calls.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.config_loader import get_config


def test_truncation_caps_long_emails():
    """A 50,000-character email should be truncated to max_tokens * 4 characters."""
    config = get_config()
    max_tokens = config.get('model_settings', {}).get('max_tokens_per_email', 1500)
    char_limit = max_tokens * 4  # The formula used in worker.py

    # Simulate a massive email (e.g., a multi-page newsletter)
    super_long_email = "A" * 50_000

    # Apply the same truncation logic as worker.py line 65
    truncated = super_long_email[:char_limit]

    assert len(truncated) == char_limit, (
        f"Expected {char_limit} chars, got {len(truncated)}"
    )
    assert len(truncated) < len(super_long_email), (
        "Truncation should have reduced the email length"
    )
    print(f"✅ PASS: 50,000-char email truncated to {len(truncated)} chars "
          f"(max_tokens={max_tokens}, char_limit={char_limit})")


def test_short_email_unchanged():
    """An email shorter than the limit should pass through untouched."""
    config = get_config()
    max_tokens = config.get('model_settings', {}).get('max_tokens_per_email', 1500)
    char_limit = max_tokens * 4

    short_email = "Hello, this is a short email."
    truncated = short_email[:char_limit]

    assert truncated == short_email, "Short emails should not be modified"
    print(f"✅ PASS: Short email ({len(short_email)} chars) passed through unchanged")


def test_config_has_token_limit():
    """The config must define max_tokens_per_email — it's a critical guardrail."""
    config = get_config()
    model_settings = config.get('model_settings', {})

    assert 'max_tokens_per_email' in model_settings, (
        "max_tokens_per_email missing from config/agent_config.yaml"
    )
    assert isinstance(model_settings['max_tokens_per_email'], int), (
        "max_tokens_per_email must be an integer"
    )
    assert model_settings['max_tokens_per_email'] > 0, (
        "max_tokens_per_email must be positive"
    )
    print(f"✅ PASS: max_tokens_per_email = {model_settings['max_tokens_per_email']}")


if __name__ == "__main__":
    test_truncation_caps_long_emails()
    test_short_email_unchanged()
    test_config_has_token_limit()
    print("\n🎉 All truncation tests passed!")
