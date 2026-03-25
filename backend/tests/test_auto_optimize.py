"""Tests for auto-optimize endpoint structure."""


def test_auto_optimize_request_validation():
    """Verify route_rewrite accepts the comment parameter."""
    from ai_providers.router import route_rewrite
    import inspect
    sig = inspect.signature(route_rewrite)
    assert "comment" in sig.parameters
    assert "threshold" in sig.parameters
