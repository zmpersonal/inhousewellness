"""Platform limits and constants. Config, never hardcoded at call sites."""

# Hard character limits enforced by each platform's API.
PLATFORM_TEXT_LIMIT = {
    "pinterest": 500,    # pin description
    "instagram": 2200,
    "facebook": 63206,
}

# Practical ceilings we impose on ourselves, well inside the API limits.
# 39 historical Facebook posts were 25,000-51,000 char article dumps
# averaging ~3 impressions. The API allowed them; we do not.
PLATFORM_TEXT_SOFT_MAX = {
    "pinterest": 350,
    "instagram": 1200,
    "facebook": 1500,
}

MIN_TEXT_CHARS = 50

# Pinterest structured-field bounds (adjustment C4).
PIN_TITLE_MIN, PIN_TITLE_MAX = 40, 100
PIN_ALT_MIN, PIN_ALT_MAX = 50, 125

SUPPORTED_PLATFORMS = frozenset(PLATFORM_TEXT_LIMIT)

# Only these hosts may appear in a destination link.
ALLOWED_LINK_HOSTS = frozenset({"inhousewellness.com", "www.inhousewellness.com"})
