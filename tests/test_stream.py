"""Test sample sync."""
from singer_sdk.testing import get_standard_tap_tests
from tap_custom_amazon_sp.tap import TapAmazonSeller
from tap_custom_amazon_sp.streams import OrdersStream

SAMPLE_CONFIG = {
    "lwa_client_id":"amzn1.application-oa2-client.1bc596a3afab44fe839b12091d859f5",
    "client_secret":"amzn1.oa2-cs.v1.49cd90e52f2dc21648e5ac2be56ab1750d396a6512baedbd7835b28f868674e7",
    "refresh_token":"Atzr|IwEBICJWgLsPQ09TLztkhmhwJecJuMJ6D32g9QDz9xHiQvvmJ11IK61Vc3hSFsMFNrHVnhavW9HxHF9WcnLbFM4j5rjtOYJqEm01Ysdh-oBplMcwxDn3xIylOafodvJI3TPfJfvpjnxOWoLD--KZS9eKGKQqDvXSloGsSCMkuf2AE5mtjQDJJms0lOmL-Mk0-bhH_kkUtq8ypb82Q9lefZcsWP9PVEuQhvTLE2RyCZK05nusCspB6pOoqy97QsWoHNNGoxYr65aUSlsFVJNtjn_sfuSDKinsHCqlI6OiUM8-0CpbK5Rkn2WiGclVbWO5nC5cgorSdYed1ChDcrcmbSeyI1an",
    "start_date": "2024-04-08T00:00:00Z"
  }

STREAM_TYPES = [
    OrdersStream
]

# Run standard built-in tap tests from the SDK:
def test_standard_tap_tests():
    """Run standard tap tests from the SDK."""
    tests = get_standard_tap_tests(
        TapAmazonSeller,
        config=SAMPLE_CONFIG
    )
    for test in tests:
        test()