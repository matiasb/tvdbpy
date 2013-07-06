

class APIClientNotAvailableError(Exception):
    """TvDB API client not available."""


class APIKeyRequiredError(Exception):
    """TvDB API key required."""


class APIResponseError(Exception):
    """Unexpected response from the TvDB API."""
