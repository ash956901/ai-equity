"""Compatibility checks for legacy external_apis wrappers."""


def test_legacy_external_api_imports_resolve_to_provider_implementations():
    from src.external_apis import ALL_EXTERNAL_ROUTERS
    from src.external_apis.FMP_api.client import FMPClient
    from src.external_apis.FRED_api.client import FREDClient
    from src.external_apis.Kite_api.client import KiteClient
    from src.external_apis.NewsAPI.client import NewsAPIClient
    from src.external_apis.NewsDataIO.client import NewsDataIOClient
    from src.external_apis.Upstox_api.client import UpstoxClient

    assert len(ALL_EXTERNAL_ROUTERS) == 6
    assert FMPClient.__name__ == "FMPClient"
    assert FREDClient.__name__ == "FREDClient"
    assert KiteClient.__name__ == "KiteClient"
    assert NewsAPIClient.__name__ == "NewsAPIClient"
    assert NewsDataIOClient.__name__ == "NewsDataIOClient"
    assert UpstoxClient.__name__ == "UpstoxClient"
