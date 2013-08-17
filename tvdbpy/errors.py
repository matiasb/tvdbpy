
class TvDBException(Exception):
    """Common base exception for TvDBpy."""


class APIClientNotAvailableError(TvDBException):
    """TvDB API client not available."""


class APIKeyRequiredError(TvDBException):
    """TvDB API key required."""


class APIResponseError(TvDBException):
    """Unexpected response from the TvDB API."""
