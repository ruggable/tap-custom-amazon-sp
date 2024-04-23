"""Amazon-Seller tap class."""

from typing import List

from singer_sdk import Stream, Tap
from singer_sdk import typing as th  # JSON schema typing helpers

from tap_custom_amazon_sp.streams import (
    AmazonSellerStream,
    MarketplacesStream,
    OrderAddress,
    OrderBuyerInfo,
    OrderFinancialEvents,
    OrderItemsStream,
    OrdersStream,
    ReportsStream,
    WarehouseInventory,
    ProductsIventoryStream,
    ProductDetails,
    VendorPurchaseOrdersStream,
    VendorFulfilmentPurchaseOrdersStream,
    VendorFulfilmentCustomerInvoicesStream,
    AFNInventoryCountryStream,
    SalesTrafficReportStream,
    FBAInventoryLedgerDetailedReportStream,
    FBACustomerShipmentSalesReportStream,
    ListFinancialEventsEntity,
    ListFullFinancialEvents
)

STREAM_TYPES = [
    OrdersStream,
    OrderItemsStream,
    MarketplacesStream,
    OrderBuyerInfo,
    OrderAddress,
    OrderFinancialEvents,
    ReportsStream,
    WarehouseInventory,
    ProductsIventoryStream,
    ProductDetails,
    VendorPurchaseOrdersStream,
    VendorFulfilmentPurchaseOrdersStream,
    VendorFulfilmentCustomerInvoicesStream,
    AFNInventoryCountryStream,
    SalesTrafficReportStream,
    FBAInventoryLedgerDetailedReportStream,
    FBACustomerShipmentSalesReportStream,
    ListFinancialEventsEntity,
    ListFullFinancialEvents
]


class TapAmazonSeller(Tap):
    """Amazon-Seller tap class."""

    name = "tap-custom-amazon-sp"

    config_jsonschema = th.PropertiesList(
        th.Property("lwa_client_id", th.StringType, required=True),
        th.Property("client_secret", th.StringType, required=True),
        th.Property("refresh_token", th.StringType, required=True),
        th.Property("sandbox", th.BooleanType, default=False),
        th.Property("start_date", th.StringType, required=False),
        th.Property("entity", th.StringType, required=False),
        th.Property(
            "report_types",
            th.CustomType({"type": ["array", "string"]}),
            default=["GET_LEDGER_DETAIL_VIEW_DATA", "GET_MERCHANT_LISTINGS_ALL_DATA"],
        ),
        th.Property(
            "processing_status",
            th.CustomType({"type": ["array", "string"]}),
            default=["IN_QUEUE", "IN_PROGRESS"],
        ),
        th.Property(
            "marketplaces",
            th.CustomType({"type": ["array", "string"]}),
            default=["US"],
        ),
    ).to_dict()

    def discover_streams(self) -> List[Stream]:
        """Return a list of discovered streams."""
        return [stream_class(tap=self) for stream_class in STREAM_TYPES]


if __name__ == "__main__":
    TapAmazonSeller.cli()
