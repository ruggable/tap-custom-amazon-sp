"""Stream type classes for tap-amazon-seller."""
from datetime import datetime, timedelta
from typing import Iterable, Optional

import backoff
from singer_sdk import typing as th
from sp_api.util import load_all_pages

from tap_custom_amazon_sp.client import AmazonSellerStream
from tap_custom_amazon_sp.utils import InvalidResponse, timeout
from sp_api.base.exceptions import SellingApiServerException
from dateutil.relativedelta import relativedelta
from sp_api.base import Marketplaces
from dateutil.parser import parse
import time

import sys
if sys.version_info >= (3, 9):
    import importlib.resources as importlib_resources
else:
    import importlib_resources

SCHEMAS_DIR = importlib_resources.files(__package__) / "schemas"

class MarketplacesStream(AmazonSellerStream):
    """Define custom stream."""

    name = "marketplaces"
    primary_keys = ["id"]
    replication_key = None
    schema = th.PropertiesList(
        th.Property("id", th.StringType),
        th.Property("name", th.StringType),
    ).to_dict()

    def get_child_context(self, record: dict, context: Optional[dict]) -> dict:
        """Return a context dictionary for child streams."""
        return {
            "marketplace_id": record["id"],
        }

    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=10,
        factor=3,
    )
    @timeout(15)
    def get_records(self, context: Optional[dict]) -> Iterable[dict]:
        if self.config.get("marketplace"):
            marketplaces = self.config.get("marketplace")
        else:
            marketplaces = [
                "US",
                "CA",
                "MX",
                "BR",
                "ES",
                "GB",
                "FR",
                "NL",
                "DE",
                "IT",
                "SE",
                "PL",
                "EG",
                "TR",
                "SA",
                "AE",
                "IN",
                "SG",
                "AU",
                "JP",
            ]
        # orders = self.get_sp_orders()
        # Fetch minimum number of orders and verify credentials are working
        today_date = datetime.today().strftime("%Y-%m-%d")
        for mp in marketplaces:
            try:
                orders = self.get_sp_orders(mp)
                sandbox = self.config.get("sandbox", False)
                if sandbox is True:
                    allorders = orders.get_orders(CreatedAfter="TEST_CASE_200")
                else:
                    allorders = orders.get_orders(CreatedAfter=today_date)
                yield {"id": mp}
                if sandbox is True:
                    # Since all sandbox orders are same and we found a valid marketplace. Break the loop.
                    break
            except Exception as e:
                if "invalid grant parameter" in e.message:
                    raise Exception(e.message)
                self.logger.info(f"marketplace {mp} not part of current SP account")


class OrdersStream(AmazonSellerStream):
    """Define custom stream."""

    name = "orders"
    primary_keys = ["AmazonOrderId"]
    replication_key = "LastUpdateDate"
    records_jsonpath = "$.Orders[*]"
    parent_stream_type = MarketplacesStream
    marketplace_id = "{marketplace_id}"

    schema = th.PropertiesList(
        th.Property("AmazonOrderId", th.StringType),
        th.Property("SellerOrderId", th.StringType),
        th.Property("PurchaseDate", th.DateTimeType),
        th.Property("LastUpdateDate", th.DateTimeType),
        th.Property("OrderStatus", th.StringType),
        th.Property("FulfillmentChannel", th.StringType),
        th.Property("SalesChannel", th.StringType),
        th.Property("ShipServiceLevel", th.StringType),
        th.Property("OrderChannel", th.StringType),
        th.Property(
            "OrderTotal",
            th.ObjectType(
                th.Property("CurrencyCode", th.StringType),
                th.Property("Amount", th.StringType),
            ),
        ),
        th.Property("NumberOfItemsShipped", th.NumberType),
        th.Property("NumberOfItemsUnshipped", th.NumberType),
        th.Property("PaymentMethod", th.StringType),
        th.Property(
            "PaymentMethodDetails", th.CustomType({"type": ["array", "string"]})
        ),
        th.Property(
            "PaymentExecutionDetail", th.CustomType({"type": ["array", "string"]})
        ),
        th.Property(
            "BuyerTaxInformation", th.CustomType({"type": ["object", "string"]})
        ),
        th.Property(
            "MarketplaceTaxInfo", th.CustomType({"type": ["object", "string"]})
        ),
        th.Property("ShippingAddress", th.CustomType({"type": ["object", "string"]})),
        th.Property("BuyerInfo", th.CustomType({"type": ["object", "string"]})),
        th.Property("IsReplacementOrder", th.BooleanType),
        th.Property("ReplacedOrderId", th.StringType),
        th.Property("MarketplaceId", th.StringType),
        th.Property("SellerDisplayName", th.StringType),
        th.Property("EasyShipShipmentStatus", th.StringType),
        th.Property("CbaDisplayableShippingLabel", th.StringType),
        th.Property("ShipmentServiceLevelCategory", th.StringType),
        th.Property("BuyerInvoicePreference", th.StringType),
        th.Property("OrderType", th.StringType),
        th.Property("EarliestShipDate", th.DateTimeType),
        th.Property("LatestShipDate", th.DateTimeType),
        th.Property("EarliestDeliveryDate", th.DateTimeType),
        th.Property("PromiseResponseDueDate", th.DateTimeType),
        th.Property("LatestDeliveryDate", th.DateTimeType),
        th.Property("IsBusinessOrder", th.BooleanType),
        th.Property("IsEstimatedShipDateSet", th.BooleanType),
        th.Property("IsPrime", th.BooleanType),
        th.Property("IsGlobalExpressEnabled", th.BooleanType),
        th.Property("HasRegulatedItems", th.BooleanType),
        th.Property("IsPremiumOrder", th.BooleanType),
        th.Property("IsSoldByAB", th.BooleanType),
        th.Property("IsIBA", th.BooleanType),
        th.Property(
            "DefaultShipFromLocationAddress",
            th.ObjectType(
                th.Property("Name", th.StringType),
                th.Property("AddressLine1", th.StringType),
                th.Property("City", th.StringType),
                th.Property("StateOrRegion", th.StringType),
                th.Property("PostalCode", th.StringType),
                th.Property("CountryCode", th.StringType),
                th.Property("Phone", th.StringType),
                th.Property("AddressType", th.StringType),
            ),
        ),
        th.Property(
            "FulfillmentInstruction",
            th.ObjectType(
                th.Property("FulfillmentSupplySourceId", th.StringType),
                th.Property("IsISPU", th.BooleanType),
            ),
        ),
        th.Property(
            "AutomatedShippingSettings",
            th.ObjectType(th.Property("HasAutomatedShippingSettings", th.BooleanType)),
        ),
    ).to_dict()

    @backoff.on_exception(
        backoff.expo,
        (Exception),
        max_tries=10,
        factor=3,
    )
    @timeout(15)
    @load_all_pages()
    def load_all_orders(self, mp, **kwargs):
        """
        a generator function to return all pages, obtained by NextToken
        """
        try:
            orders = self.get_sp_orders(mp)
            orders_obj = orders.get_orders(**kwargs)
            return orders_obj
        except Exception as e:
            raise InvalidResponse(e)

    def load_order_page(self, mp, **kwargs):
        """
        a generator function to return all pages, obtained by NextToken
        """

        for page in self.load_all_orders(mp, **kwargs):
            orders = []
            for order in page.payload.get("Orders"):
                orders.append(order)

            yield orders

    @backoff.on_exception(
        backoff.expo,
        (Exception),
        max_tries=10,
        factor=3,
    )
    def get_records(self, context: Optional[dict]) -> Iterable[dict]:
        try:
            # Get start_date
            start_date = self.get_starting_timestamp(context) or datetime(2000, 1, 1)
            start_date = start_date.strftime("%Y-%m-%dT%H:%M:%S")
            end_date = None
            if self.config.get("end_date"):
                end_date = parse(self.config.get("end_date"))
                end_date = end_date.strftime("%Y-%m-%dT%H:%M:%S")
                

            sandbox = self.config.get("sandbox", False)
            if sandbox is True:
                rows = self.load_order_page(
                    mp=context.get("marketplace_id"), CreatedAfter="TEST_CASE_200"
                )
            else:
                if start_date and end_date:
                    rows = self.load_order_page(
                        mp=context.get("marketplace_id"), 
                        LastUpdatedAfter=start_date,
                        LastUpdatedBefore = end_date
                    )
                else:
                    rows = self.load_order_page(
                        mp=context.get("marketplace_id"), 
                        LastUpdatedAfter=start_date
                    )    
            for row in rows:
                for item in row:
                    yield item
        except Exception as e:
            raise InvalidResponse(e)

    def get_child_context(self, record: dict, context: Optional[dict]) -> dict:
        """Return a context dictionary for child streams."""
        mp = context.get("marketplace_id")
        return {"AmazonOrderId": record["AmazonOrderId"], "marketplace_id": mp}


class OrderItemsStream(AmazonSellerStream):
    """Define custom stream."""

    name = "orderitems"
    primary_keys = ["OrderItemId"]
    replication_key = None
    order_id = "{AmazonOrderId}"
    parent_stream_type = OrdersStream
    schema_writed = False

    schema = th.PropertiesList(
        th.Property("AmazonOrderId", th.StringType),
        th.Property(
            "OrderItems",
            th.ArrayType(
                th.ObjectType(
                    th.Property("ASIN", th.StringType),
                    th.Property("OrderItemId", th.StringType),
                    th.Property("SellerSKU", th.StringType),
                    th.Property("Title", th.StringType),
                    th.Property("QuantityOrdered", th.NumberType),
                    th.Property("QuantityShipped", th.NumberType),
                    th.Property(
                        "ProductInfo", th.CustomType({"type": ["object", "string"]})
                    ),
                    th.Property(
                        "PointsGranted", th.CustomType({"type": ["object", "string"]})
                    ),
                    th.Property(
                        "ItemPrice", th.CustomType({"type": ["object", "string"]})
                    ),
                    th.Property(
                        "ShippingPrice", th.CustomType({"type": ["object", "string"]})
                    ),
                    th.Property(
                        "ShippingDiscount",
                        th.CustomType({"type": ["object", "string"]}),
                    ),
                    th.Property(
                        "ShippingDiscountTax",
                        th.CustomType({"type": ["object", "string"]}),
                    ),
                    th.Property(
                        "PromotionDiscount",
                        th.CustomType({"type": ["object", "string"]}),
                    ),
                    th.Property(
                        "PromotionDiscountTax",
                        th.CustomType({"type": ["object", "string"]}),
                    ),
                    th.Property(
                        "ItemTax", th.CustomType({"type": ["object", "string"]})
                    ),
                    th.Property(
                        "ShippingTax", th.CustomType({"type": ["object", "string"]})
                    ),
                    th.Property(
                        "PromotionIds", th.CustomType({"type": ["array", "string"]})
                    ),
                    th.Property(
                        "CODFee", th.CustomType({"type": ["object", "string"]})
                    ),
                    th.Property(
                        "CODFeeDiscount", th.CustomType({"type": ["object", "string"]})
                    ),
                    th.Property(
                        "TaxCollection", th.CustomType({"type": ["object", "string"]})
                    ),
                    th.Property(
                        "BuyerInfo", th.CustomType({"type": ["object", "string"]})
                    ),
                    th.Property(
                        "BuyerRequestedCancel",
                        th.CustomType({"type": ["object", "string"]}),
                    ),
                    th.Property("IsGift", th.StringType),
                    th.Property("ConditionId", th.StringType),
                    th.Property("ConditionNote", th.StringType),
                    th.Property("ConditionSubtypeId", th.StringType),
                    th.Property("ScheduledDeliveryStartDate", th.StringType),
                    th.Property("ScheduledDeliveryEndDate", th.StringType),
                    th.Property("PriceDesignation", th.StringType),
                    th.Property("IsTransparency", th.BooleanType),
                    th.Property("SerialNumberRequired", th.BooleanType),
                    th.Property("IossNumber", th.StringType),
                    th.Property("DeemedResellerCategory", th.StringType),
                    th.Property("StoreChainStoreId", th.StringType),
                    th.Property(
                        "BuyerRequestedCancel",
                        th.CustomType({"type": ["object", "string"]}),
                    ),
                )
            ),
        ),
    ).to_dict()

    @backoff.on_exception(
        backoff.expo,
        (Exception),
        max_tries=10,
        factor=3,
    )
    @timeout(15)
    def get_records(self, context: Optional[dict]) -> Iterable[dict]:
        try:
            order_id = context.get("AmazonOrderId", [])

            orders = self.get_sp_orders(context.get("marketplace_id"))
            # self.state_partitioning_keys = context
            self.state_partitioning_keys = self.partitions[len(self.partitions) - 1]
            # self.state_partitioning_keys = self.partitions
            sandbox = self.config.get("sandbox", False)
            if sandbox is False:
                items = orders.get_order_items(order_id=order_id).payload
            else:
                items = orders.get_order_items("'TEST_CASE_200'").payload
            return [items]
        except Exception as e:
            raise InvalidResponse(e)


class OrderBuyerInfo(AmazonSellerStream):
    """Define custom stream."""

    name = "orderbuyerinfo"
    primary_keys = ["AmazonOrderId"]
    replication_key = None
    order_id = "{AmazonOrderId}"
    parent_stream_type = OrdersStream
    # Optionally, you may also use `schema_filepath` in place of `schema`:
    # schema_filepath = SCHEMAS_DIR / "users.json"
    schema = th.PropertiesList(
        th.Property("AmazonOrderId", th.StringType),
        th.Property("BuyerEmail", th.StringType),
        th.Property("BuyerName", th.StringType),
        th.Property("BuyerCounty", th.StringType),
        th.Property("BuyerTaxInfo", th.CustomType({"type": ["object", "string"]})),
        th.Property("PurchaseOrderNumber", th.StringType),
    ).to_dict()

    @backoff.on_exception(
        backoff.expo,
        (Exception),
        max_tries=10,
        factor=3,
    )
    @timeout(15)
    def get_records(self, context: Optional[dict]) -> Iterable[dict]:
        try:
            order_id = context.get("AmazonOrderId", [])

            orders = self.get_sp_orders(context.get("marketplace_id"))
            items = orders.get_order_buyer_info(order_id=order_id).payload
            return [items]
        except Exception as e:
            raise InvalidResponse(e)


class OrderAddress(AmazonSellerStream):
    """Define custom stream."""

    name = "orderaddress"
    primary_keys = ["AmazonOrderId"]
    replication_key = None
    order_id = "{AmazonOrderId}"
    parent_stream_type = OrdersStream
    # Optionally, you may also use `schema_filepath` in place of `schema`:
    # schema_filepath = SCHEMAS_DIR / "users.json"
    schema = th.PropertiesList(
        th.Property("AmazonOrderId", th.StringType),
        th.Property(
            "ShippingAddress",
            th.ObjectType(
                th.Property("Name", th.StringType),
                th.Property("AddressLine1", th.StringType),
                th.Property("AddressLine2", th.StringType),
                th.Property("AddressLine3", th.StringType),
                th.Property("City", th.StringType),
                th.Property("County", th.StringType),
                th.Property("District", th.StringType),
                th.Property("StateOrRegion", th.StringType),
                th.Property("Municipality", th.StringType),
                th.Property("PostalCode", th.StringType),
                th.Property("CountryCode", th.StringType),
                th.Property("Phone", th.StringType),
                th.Property("AddressType", th.StringType),
            ),
        ),
    ).to_dict()

    @backoff.on_exception(
        backoff.expo,
        (Exception),
        max_tries=10,
        factor=3,
    )
    @timeout(15)
    def get_records(self, context: Optional[dict]) -> Iterable[dict]:
        try:
            order_id = context.get("AmazonOrderId", [])

            orders = self.get_sp_orders(context.get("marketplace_id"))
            items = orders.get_order_address(order_id=order_id).payload
            return [items]
        except Exception as e:
            raise InvalidResponse(e)


class OrderFinancialEvents(AmazonSellerStream):
    """Define custom stream."""

    name = "orderfinancialevents"
    primary_keys = ["AmazonOrderId"]
    replication_key = None
    order_id = "{AmazonOrderId}"
    parent_stream_type = OrdersStream
    # Optionally, you may also use `schema_filepath` in place of `schema`:
    # schema_filepath = SCHEMAS_DIR / "users.json"
    schema = th.PropertiesList(
        th.Property("AmazonOrderId", th.StringType),
        th.Property("ShipmentEventList", th.CustomType({"type": ["array", "string"]})),
        th.Property("RefundEventList", th.CustomType({"type": ["array", "string"]})),
        th.Property(
            "GuaranteeClaimEventList", th.CustomType({"type": ["array", "string"]})
        ),
        th.Property(
            "ChargebackEventList", th.CustomType({"type": ["array", "string"]})
        ),
        th.Property(
            "PayWithAmazonEventList", th.CustomType({"type": ["array", "string"]})
        ),
        th.Property(
            "ServiceProviderCreditEventList",
            th.CustomType({"type": ["array", "string"]}),
        ),
        th.Property(
            "RetrochargeEventList", th.CustomType({"type": ["array", "string"]})
        ),
        th.Property(
            "RentalTransactionEventList", th.CustomType({"type": ["array", "string"]})
        ),
        th.Property(
            "ProductAdsPaymentEventList", th.CustomType({"type": ["array", "string"]})
        ),
        th.Property(
            "ServiceFeeEventList", th.CustomType({"type": ["array", "string"]})
        ),
        th.Property(
            "SellerDealPaymentEventList", th.CustomType({"type": ["array", "string"]})
        ),
        th.Property(
            "DebtRecoveryEventList", th.CustomType({"type": ["array", "string"]})
        ),
        th.Property(
            "LoanServicingEventList", th.CustomType({"type": ["array", "string"]})
        ),
        th.Property(
            "AdjustmentEventList", th.CustomType({"type": ["array", "string"]})
        ),
        th.Property(
            "SAFETReimbursementEventList", th.CustomType({"type": ["array", "string"]})
        ),
        th.Property(
            "SellerReviewEnrollmentPaymentEventList",
            th.CustomType({"type": ["array", "string"]}),
        ),
        th.Property(
            "FBALiquidationEventList", th.CustomType({"type": ["array", "string"]})
        ),
        th.Property(
            "CouponPaymentEventList", th.CustomType({"type": ["array", "string"]})
        ),
        th.Property(
            "ImagingServicesFeeEventList", th.CustomType({"type": ["array", "string"]})
        ),
        th.Property(
            "NetworkComminglingTransactionEventList",
            th.CustomType({"type": ["array", "string"]}),
        ),
        th.Property(
            "AffordabilityExpenseEventList",
            th.CustomType({"type": ["array", "string"]}),
        ),
        th.Property(
            "AffordabilityExpenseReversalEventList",
            th.CustomType({"type": ["array", "string"]}),
        ),
        th.Property(
            "TrialShipmentEventList", th.CustomType({"type": ["array", "string"]})
        ),
        th.Property(
            "ShipmentSettleEventList", th.CustomType({"type": ["array", "string"]})
        ),
        th.Property(
            "TaxWithholdingEventList", th.CustomType({"type": ["array", "string"]})
        ),
        th.Property(
            "RemovalShipmentEventList", th.CustomType({"type": ["array", "string"]})
        ),
        th.Property(
            "RemovalShipmentAdjustmentEventList",
            th.CustomType({"type": ["array", "string"]}),
        ),
    ).to_dict()

    @backoff.on_exception(
        backoff.expo,
        (Exception),
        max_tries=10,
        factor=3,
    )
    @timeout(15)
    def get_records(self, context: Optional[dict]) -> Iterable[dict]:
        try:
            order_id = context.get("AmazonOrderId", [])

            finance = self.get_sp_finance(context.get("marketplace_id"))

            sandbox = self.config.get("sandbox", False)
            if sandbox is False:
                # self.state_partitioning_keys = self.partitions
                self.state_partitioning_keys = self.partitions[len(self.partitions) - 1]
                items = finance.get_financial_events_for_order(order_id).payload
                items["AmazonOrderId"] = order_id
            else:
                items = finance.get_financial_events_for_order("TEST_CASE_200").payload
            return [items["FinancialEvents"]]
        except Exception as e:
            raise InvalidResponse(e)

class ListFinancialEvents(AmazonSellerStream):
    """Define custom stream."""

    name = "listfinancialevents"
    primary_keys = ["AmazonOrderId"]
    #replication_key = "PostedDate"
    #records_jsonpath = "$.FinancialEvents[*]"
    #parent_stream_type = MarketplacesStream
    #marketplace_id = "{marketplace_id}"

    # Optionally, you may also use `schema_filepath` in place of `schema`:
    #schema_filepath = SCHEMAS_DIR / "list-financial-events.json"
    @property
    def replication_key(self):
        """Return entity dynamically based on user inputs."""
        entity = self.config.get("entity")
        if entity is not None:
            replication_key = "PostedDate"
        else: 
            replication_key = None   
        return replication_key

    @property
    def schema_filepath(self):
        """Return entity dynamically based on user inputs."""
        entity = self.config.get("entity")
        if entity is not None:
            schema_filepath = SCHEMAS_DIR / f"{entity}.json"
        else: 
            schema_filepath = SCHEMAS_DIR / "list-financial-events-custom-entities.json"   
        return schema_filepath

    @backoff.on_exception(
        backoff.expo,
        (Exception),
        max_tries=10,
        factor=3,
    )

    @timeout(15)
    @load_all_pages()
    def load_all_financial_events(self, mp=Optional[list], **kwargs):
        """
        a generator function to return all pages, obtained by NextToken
        """
        try:
            finance = self.get_sp_finance()
            finance_obj = finance.list_financial_events(**kwargs)
            return finance_obj
        except Exception as e:
            raise InvalidResponse(e)

    def load_finance_page(self, mp=Optional[list], **kwargs):
        """
        a generator function to return all pages, obtained by NextToken
        """
        entity = self.config.get("entity")
        for page in self.load_all_financial_events(mp=Optional[list], **kwargs):
            events = []
            if entity is not None:
                endpoint = page.payload.get("FinancialEvents").get(entity)
                for event in endpoint:
                    events.append(event)
            else:
                endpoint = page.payload.get("FinancialEvents")
                events.append(endpoint)
            yield events

    @timeout(15)
    def get_records(self, context: Optional[dict]) -> Iterable[dict]:
        try:
            start_date = self.get_starting_timestamp(context) or datetime(2022, 1, 1)
            end_date = None
            if self.config.get("start_date"):
                start_date = parse(self.config.get("start_date"))
            if self.config.get("end_date"):
                end_date = parse(self.config.get("end_date"))

            start_date = start_date.strftime("%Y-%m-%dT00:00:00")
            sandbox = self.config.get("sandbox", False)

            if sandbox is True:
                rows = self.load_finance_page(PostedAfter="TEST_CASE_200")
            else:
                if start_date and end_date:
                    rows = self.load_finance_page(
                        PostedAfter=start_date,
                        PostedBefore = end_date
                    )
                else:
                    rows = self.load_finance_page( 
                        PostedAfter=start_date
                    )    
            for row in rows:
                for item in row:
                    yield item
        except Exception as e:
            raise InvalidResponse(e)

    # @timeout(15)
    # def get_records(self, context: Optional[dict]) -> Iterable[dict]:
    #     try:
    #         start_date = self.get_starting_timestamp(context) or datetime(2022, 1, 1)
    #         end_date = None
    #         if self.config.get("start_date"):
    #             start_date = parse(self.config.get("start_date"))
    #         if self.config.get("end_date"):
    #             end_date = parse(self.config.get("end_date"))

    #         start_date = start_date.strftime("%Y-%m-%dT00:00:00")

    #         finance = self.get_sp_finance()
    #         sandbox = self.config.get("sandbox", False)
    #         if sandbox is False:
    #             self.state_partitioning_keys = self.partitions[len(self.partitions) - 1]
    #             items = finance.list_financial_events(PostedAfter=start_date,PostedBefore=end_date).payload
    #         else:
    #             items = finance.list_financial_events("TEST_CASE_200").payload
        
    #         return [items["FinancialEvents"]]

            
        except Exception as e:
            raise InvalidResponse(e)


class ReportsStream(AmazonSellerStream):
    """Define custom stream."""

    name = "reports"
    primary_keys = ["reportId"]
    replication_key = None
    report_id = None
    document_id = None
    schema = th.PropertiesList(
        th.Property("marketplaceIds", th.CustomType({"type": ["array", "string"]})),
        th.Property("reportId", th.StringType),
        th.Property("Date", th.DateTimeType),
        th.Property("FNSKU", th.StringType),
        th.Property("ASIN", th.StringType),
        th.Property("MSKU", th.StringType),
        th.Property("Title", th.StringType),
        th.Property("Event Type", th.StringType),
        th.Property("Reference ID", th.StringType),
        th.Property("Quantity", th.StringType),
        th.Property("Fulfillment Center", th.StringType),
        th.Property("Disposition", th.StringType),
        th.Property("Reason", th.StringType),
        th.Property("Country", th.StringType),
        # th.Property("reportType", th.StringType),
        # th.Property("dataStartTime", th.DateTimeType),
        # th.Property("dataEndTime", th.DateTimeType),
        # th.Property("dataEndreportScheduleIdime", th.StringType),
        # th.Property("createdTime", th.DateTimeType),
        # th.Property("processingStatus", th.StringType),
        # th.Property("processingStartTime", th.DateTimeType),
        # th.Property("processingEndTime", th.DateTimeType),
        # th.Property("reportDocumentId", th.StringType),
    ).to_dict()

    @backoff.on_exception(
        backoff.expo,
        (Exception),
        max_tries=10,
        factor=3,
    )
    @timeout(15)
    def get_records(self, context: Optional[dict]) -> Iterable[dict]:
        try:
            start_date = self.get_starting_timestamp(context) or datetime(2005, 1, 1)
            end_date = None
            if self.config.get("start_date"):
                start_date = parse(self.config.get("start_date"))
            if self.config.get("end_date"):
                end_date = parse(self.config.get("end_date"))

            start_date = start_date.strftime("%Y-%m-%dT00:00:00")
            report_types = self.config.get("report_types")
            processing_status = self.config.get("processing_status")
            marketplace_id = None
            if context is not None:
                marketplace_id = context.get("marketplace_id")

            report = self.get_sp_reports()
            if start_date and end_date is not None:
                end_date = end_date.strftime("%Y-%m-%dT23:59:59")
                items = report.get_reports(
                    reportTypes=report_types,
                    processingStatuses=processing_status,
                    dataStartTime=start_date,
                    dataEndTime=end_date,
                ).payload
            else:
                items = report.get_reports(
                    reportTypes=report_types,
                    processingStatuses=processing_status,
                    dataStartTime=start_date,
                ).payload

            if not items["reports"]:
                reports = self.create_report(start_date, report, end_date)
                for row in reports:
                    yield row

            # If reports are form loop through, download documents and populate the data.txt
            for row in items["reports"]:
                reports = self.check_report(row["reportId"], report)
                for report_row in reports:
                    yield report_row

        except Exception as e:
            raise InvalidResponse(e)


class WarehouseInventory(AmazonSellerStream):
    """Define custom stream."""

    next_token = None
    name = "warehouse_inventory"
    primary_keys = ["asin", "fnSku", "sellerSku"]
    replication_key = None
    parent_stream_type = MarketplacesStream
    marketplace_id = "{marketplace_id}"
    schema = th.PropertiesList(
        th.Property("marketplace_id", th.StringType),
        th.Property("granularityType", th.StringType),
        th.Property("granularityId", th.StringType),
        th.Property("asin", th.StringType),
        th.Property("fnSku", th.StringType),
        th.Property("sellerSku", th.StringType),
        th.Property("condition", th.StringType),
        th.Property("lastUpdatedTime", th.DateTimeType),
        th.Property("productName", th.StringType),
        th.Property("totalQuantity", th.NumberType),
        th.Property("inventoryDetails", th.CustomType({"type": ["object", "string"]})),
    ).to_dict()

    @backoff.on_exception(
        backoff.expo,
        (Exception),
        max_tries=10,
        factor=3,
    )
    @timeout(15)
    @load_all_pages()
    def load_all_items(self, mp, **kwargs):
        """
        a generator function to return all pages, obtained by NextToken
        """
        try:
            wi = self.get_warehouse_object(mp)
            kwargs.update({"details": True})
            del kwargs["startDateTime"]
            if self.next_token is not None:
                kwargs.update({"nextToken": self.next_token})

            list = wi.get_inventory_summary_marketplace(**kwargs)
            return list
        except Exception as e:
            raise InvalidResponse(e)

    def load_item_page(self, mp, **kwargs):
        """
        a generator function to return all pages, obtained by NextToken
        """

        for page in self.load_all_items(mp, **kwargs):
            self.next_token = page.next_token
            yield page.payload

    @backoff.on_exception(
        backoff.expo,
        (Exception),
        max_tries=10,
        factor=3,
    )
    def get_records(self, context: Optional[dict]) -> Iterable[dict]:
        try:
            six_months_ago = datetime.today() - relativedelta(months=18)
            start_date = self.get_starting_timestamp(context) or six_months_ago
            start_date = start_date.strftime("%Y-%m-%dT%H:%M:%S")
            rows = self.load_item_page(
                mp=context.get("marketplace_id"), startDateTime=start_date
            )

            for row in rows:
                return_row = {"marketplace_id": context.get("marketplace_id")}
                if "granularity" in row:
                    return_row.update(row["granularity"])
                    if "inventorySummaries" in row:
                        if len(row["inventorySummaries"]) > 0:
                            for summary in row["inventorySummaries"]:
                                return_row.update(summary)
                                yield return_row
                    else:
                        return_row.update({"lastUpdatedTime": ""})
                else:
                    yield return_row
        except Exception as e:
            raise InvalidResponse(e)


class ProductsIventoryStream(AmazonSellerStream):
    """Define custom stream."""

    name = "products_inventory"
    primary_keys = ["listing-id"]
    replication_key = None
    report_id = None
    document_id = None
    parent_stream_type = MarketplacesStream
    schema = th.PropertiesList(
        th.Property("marketplaceIds", th.CustomType({"type": ["array", "string"]})),
        th.Property("item-name", th.StringType),
        th.Property("marketplace_id", th.StringType),
        th.Property("item-description", th.StringType),
        th.Property("listing-id", th.StringType),
        th.Property("seller-sku", th.StringType),
        th.Property("price", th.StringType),
        th.Property("quantity", th.StringType),
        th.Property("open-date", th.StringType),
        th.Property("image-url", th.StringType),
        th.Property("item-is-marketplace", th.StringType),
        th.Property("product-id-type", th.StringType),
        th.Property("zshop-shipping-fee", th.StringType),
        th.Property("item-note", th.StringType),
        th.Property("item-condition", th.StringType),
        th.Property("zshop-category1", th.StringType),
        th.Property("zshop-browse-path", th.StringType),
        th.Property("asin1", th.StringType),
        th.Property("asin2", th.StringType),
        th.Property("asin3", th.StringType),
        th.Property("will-ship-internationally", th.StringType),
        th.Property("zshop-boldface", th.StringType),
        th.Property("product-id", th.StringType),
        th.Property("bid-for-featured-placement", th.StringType),
        th.Property("add-delete", th.StringType),
        th.Property("pending-quantity", th.StringType),
        th.Property("fulfilment-channel", th.StringType),
        th.Property("merchant-shipping-group", th.StringType),
        th.Property("status", th.StringType),
        th.Property("Minimum order quantity", th.StringType),
        th.Property("Sell remainder", th.StringType),
        th.Property("product-id", th.StringType),
        th.Property("marketplace_id", th.StringType),
    ).to_dict()

    def get_child_context(self, record: dict, context: Optional[dict]) -> dict:
        """Return a context dictionary for child streams."""
        if "asin1" in record:
            return {
                "ASIN": record["asin1"],
                "marketplace_id": context.get("marketplace_id"),
            }
        elif "product-id" in record:
            return {
                "ASIN": record["product-id"],
                "marketplace_id": context.get("marketplace_id"),
            }
        else:
            return []

    @backoff.on_exception(
        backoff.expo,
        (Exception),
        max_tries=10,
        factor=3,
    )
    @timeout(15)
    def get_records(self, context: Optional[dict]) -> Iterable[dict]:
        try:
            start_date = self.get_starting_timestamp(context) or datetime(2005, 1, 1)
            end_date = None
            if self.config.get("start_date"):
                start_date = parse(self.config.get("start_date"))
            if self.config.get("end_date"):
                end_date = parse(self.config.get("end_date"))

            start_date = start_date.strftime("%Y-%m-%dT00:00:00")
            report_types = ["GET_MERCHANT_LISTINGS_ALL_DATA"]
            processing_status = self.config.get("processing_status")
            marketplace_id = None
            if context is not None:
                marketplace_id = context.get("marketplace_id")

            report = self.get_sp_reports(marketplace_id=marketplace_id)
            if start_date and end_date is not None:
                end_date = end_date.strftime("%Y-%m-%dT23:59:59")
                items = report.get_reports(
                    reportTypes=report_types,
                    processingStatuses=processing_status,
                    dataStartTime=start_date,
                    dataEndTime=end_date,
                ).payload
            else:
                items = report.get_reports(
                    reportTypes=report_types,
                    processingStatuses=processing_status,
                    dataStartTime=start_date,
                ).payload

            if not items["reports"]:
                reports = self.create_report(
                    start_date, report, end_date, "GET_MERCHANT_LISTINGS_ALL_DATA"
                )
                for row in reports:
                    yield row

            # If reports are form loop through, download documents and populate the data.txt
            for row in items["reports"]:
                reports = self.check_report(row["reportId"], report)
                for report_row in reports:
                    if context is not None:
                        report_row.update(
                            {marketplace_id: context.get("marketplace_id")}
                        )
                    yield report_row

        except Exception as e:
            raise InvalidResponse(e)


class ProductDetails(AmazonSellerStream):
    """Define custom stream."""

    name = "product_details"
    primary_keys = ["ASIN"]
    replication_key = None
    asin = "{ASIN}"
    parent_stream_type = ProductsIventoryStream
    # Optionally, you may also use `schema_filepath` in place of `schema`:
    # schema_filepath = SCHEMAS_DIR / "users.json"
    schema = th.PropertiesList(
        th.Property("ASIN", th.StringType),
        th.Property("Identifiers", th.CustomType({"type": ["object", "string"]})),
        th.Property("AttributeSets", th.CustomType({"type": ["array", "string"]})),
        th.Property("Relationships", th.CustomType({"type": ["array", "string"]})),
        th.Property("SalesRankings", th.CustomType({"type": ["array", "string"]})),
        th.Property("marketplace_id", th.StringType),
    ).to_dict()

    @backoff.on_exception(
        backoff.expo,
        (Exception),
        max_tries=10,
        factor=3,
    )
    @timeout(15)
    def get_records(self, context: Optional[dict]) -> Iterable[dict]:
        try:
            # if context is not None:
            asin = context.get("ASIN")
            catalog = self.get_sp_catalog(context.get("marketplace_id"))
            if context.get("marketplace_id") == "JP":
                items = catalog.list_items(JAN=asin).payload
            elif context.get("marketplace_id") in ["FR"]:
                items = catalog.list_items(EAN=asin).payload
            else:
                items = catalog.get_item(asin=asin).payload
            if "Items" in items:
                if len(items["Items"]) > 0:
                    items = items["Items"][0]
            items.update({"ASIN": asin})
            items.update({"marketplace_id": context.get("marketplace_id")})
            return [items]
            # else:
            #     return []
        except Exception as e:
            raise InvalidResponse(e)


class VendorFulfilmentPurchaseOrdersStream(AmazonSellerStream):
    """Define custom stream."""

    name = "vendor_fulfilment_purchase_orders"
    primary_keys = ["purchaseOrderNumber"]
    # TODO loook for relevant replication key in the live data
    replication_key = None
    parent_stream_type = MarketplacesStream
    marketplace_id = "{marketplace_id}"

    schema = th.PropertiesList(
        th.Property("purchaseOrderNumber", th.StringType),
        # Optional, not always populated
        th.Property(
            "orderDetails",
            th.ObjectType(
                th.Property("customerOrderNumber", th.StringType),
                th.Property("orderDate", th.DateTimeType),
                th.Property("orderStatus", th.StringType),
                th.Property(
                    "shipmentDetails", th.CustomType({"type": ["object", "string"]})
                ),
                th.Property("taxTotal", th.CustomType({"type": ["object", "string"]})),
                th.Property(
                    "sellingParty", th.CustomType({"type": ["object", "string"]})
                ),
                th.Property(
                    "shipToParty", th.CustomType({"type": ["object", "string"]})
                ),
                th.Property(
                    "billToParty", th.CustomType({"type": ["object", "string"]})
                ),
                th.Property("items", th.CustomType({"type": ["array", "string"]})),
            ),
        ),
    ).to_dict()

    @backoff.on_exception(
        backoff.expo,
        (Exception),
        max_tries=10,
        factor=3,
    )
    @timeout(15)
    @load_all_pages()
    def load_all_orders(self, mp, **kwargs):
        """
        a generator function to return all pages, obtained by NextToken
        """
        try:
            orders = self.get_sp_vendor_fulfilment(mp)
            orders_obj = orders.get_orders(**kwargs)
            return orders_obj
        except Exception as e:
            raise InvalidResponse(e)

    def load_order_page(self, mp, **kwargs):
        """
        a generator function to return all pages, obtained by NextToken
        """

        for page in self.load_all_orders(mp, **kwargs):
            orders = []
            for order in page.payload.get("Orders"):
                orders.append(order)

            yield orders

    @backoff.on_exception(
        backoff.expo,
        (Exception),
        max_tries=10,
        factor=3,
    )
    def get_records(self, context: Optional[dict]) -> Iterable[dict]:
        try:
            # Get start_date
            start_date = self.get_starting_timestamp(context) or datetime(2000, 1, 1)
            start_date = start_date.strftime("%Y-%m-%dT%H:%M:%S")
            if self.config.get("end_date"):
                end_date = parse(self.config.get("end_date"))
            else:
                # End date required by the endpoint
                end_date = datetime.today().strftime("%Y-%m-%dT%H:%M:%S.%fZ")

            sandbox = self.config.get("sandbox", False)
            if sandbox is True:
                rows = self.load_order_page(
                    mp=context.get("marketplace_id"), CreatedAfter="TEST_CASE_200"
                )
            else:
                rows = self.load_order_page(
                    mp=context.get("marketplace_id"),
                    createdBefore=end_date,
                    createdAfter=start_date,
                )
            for row in rows:
                for item in row:
                    yield item
        except Exception as e:
            raise InvalidResponse(e)


class VendorFulfilmentCustomerInvoicesStream(AmazonSellerStream):
    """Define custom stream."""

    name = "vendor_fulfilment_customer_invoices"
    primary_keys = ["purchaseOrderNumber"]
    # TODO loook for relevant key in live data
    replication_key = None
    parent_stream_type = MarketplacesStream
    marketplace_id = "{marketplace_id}"

    schema = th.PropertiesList(
        th.Property("purchaseOrderNumber", th.StringType),
        th.Property("content", th.StringType),
        th.Property("sellingParty", th.CustomType({"type": ["object", "string"]})),
        th.Property("shipFromParty", th.CustomType({"type": ["object", "string"]})),
        th.Property("labelFormat", th.CustomType({"type": ["object", "string"]})),
        th.Property("labelData", th.CustomType({"type": ["array", "string"]})),
    ).to_dict()

    @backoff.on_exception(
        backoff.expo,
        (Exception),
        max_tries=10,
        factor=3,
    )
    @timeout(15)
    @load_all_pages()
    def load_all_orders(self, mp, **kwargs):
        """
        a generator function to return all pages, obtained by NextToken
        """
        try:
            vendor_shipping = self.get_sp_vendor_fulfilment_shipping(mp)
            invoices_obj = vendor_shipping.get_orders(**kwargs)
            return invoices_obj
        except Exception as e:
            raise InvalidResponse(e)

    def load_order_page(self, mp, **kwargs):
        """
        a generator function to return all pages, obtained by NextToken
        """

        for page in self.load_all_orders(mp, **kwargs):
            orders = []
            for order in page.payload.get("shippingLabels"):
                orders.append(order)

            yield orders

    @backoff.on_exception(
        backoff.expo,
        (Exception),
        max_tries=10,
        factor=3,
    )
    def get_records(self, context: Optional[dict]) -> Iterable[dict]:
        try:
            # Get start_date
            start_date = self.get_starting_timestamp(context) or datetime(2000, 1, 1)
            start_date = start_date.strftime("%Y-%m-%dT%H:%M:%S")
            if self.config.get("end_date"):
                end_date = parse(self.config.get("end_date"))
            else:
                # End date required by the endpoint
                end_date = datetime.today().strftime("%Y-%m-%dT%H:%M:%S.%fZ")

            sandbox = self.config.get("sandbox", False)
            if sandbox is True:
                rows = self.load_order_page(
                    mp=context.get("marketplace_id"), CreatedAfter="TEST_CASE_200"
                )
            else:
                rows = self.load_order_page(
                    mp=context.get("marketplace_id"),
                    createdBefore=end_date,
                    createdAfter=start_date,
                )
            for row in rows:
                for item in row:
                    yield item
        except Exception as e:
            raise InvalidResponse(e)


class VendorPurchaseOrdersStream(AmazonSellerStream):
    """Define custom stream."""

    name = "vendor_purchase_orders"
    primary_keys = ["purchaseOrderNumber"]
    # TODO loook for relevant replication key in the live data
    replication_key = None
    parent_stream_type = MarketplacesStream
    marketplace_id = "{marketplace_id}"

    schema = th.PropertiesList(
        th.Property("purchaseOrderNumber", th.StringType),
        th.Property("purchaseOrderState", th.StringType),
        # Optional, not always populated
        th.Property("orderDetails", th.CustomType({"type": ["object", "string"]})),
        th.Property("deliveryWindow", th.StringType),
        th.Property("items", th.CustomType({"type": ["array", "string"]})),
    ).to_dict()

    @backoff.on_exception(
        backoff.expo,
        (Exception),
        max_tries=10,
        factor=3,
    )
    @timeout(15)
    @load_all_pages()
    def load_all_orders(self, mp, **kwargs):
        """
        a generator function to return all pages, obtained by NextToken
        """
        try:
            orders = self.get_sp_vendor(mp)
            orders_obj = orders.get_purchase_orders(**kwargs)
            return orders_obj
        except Exception as e:
            raise InvalidResponse(e)

    def load_order_page(self, mp, **kwargs):
        """
        a generator function to return all pages, obtained by NextToken
        """

        for page in self.load_all_orders(mp, **kwargs):
            orders = []
            for order in page.payload.get("Orders"):
                orders.append(order)

            yield orders

    @backoff.on_exception(
        backoff.expo,
        (Exception),
        max_tries=10,
        factor=3,
    )
    def get_records(self, context: Optional[dict]) -> Iterable[dict]:
        try:
            # Get start_date
            start_date = self.get_starting_timestamp(context) or datetime.today()
            start_date = start_date.strftime("%Y-%m-%dT%H:%M:%S")
            if self.config.get("end_date"):
                end_date = parse(self.config.get("end_date"))
            else:
                # End date required by the endpoint
                end_date = datetime.today().strftime("%Y-%m-%dT%H:%M:%S.%fZ")

            sandbox = self.config.get("sandbox", False)
            if sandbox is True:
                rows = self.load_order_page(
                    mp=context.get("marketplace_id"), CreatedAfter="TEST_CASE_200"
                )
            else:
                rows = self.load_order_page(
                    mp=context.get("marketplace_id"),
                    createdAfter=start_date,
                    limit=100,
                    SortOrder="DESC",
                )
            for row in rows:
                for item in row:
                    yield item
        except Exception as e:
            raise InvalidResponse(e)


class AFNInventoryCountryStream(AmazonSellerStream):
    """Define custom stream."""

    name = "afn_inventory_country"
    primary_keys = None
    replication_key = None
    report_id = None
    document_id = None
    schema = th.PropertiesList(
        th.Property("seller-sku", th.StringType),
        th.Property("fulfillment-channel-sku", th.StringType),
        th.Property("asin", th.StringType),
        th.Property("condition-type", th.StringType),
        th.Property("country", th.StringType),
        th.Property("quantity-for-local-fulfillment", th.StringType),
    ).to_dict()

    def get_child_context(self, record: dict, context: Optional[dict]) -> dict:
        """Return a context dictionary for child streams."""
        if "asin1" in record:
            return {
                "ASIN": record["asin1"],
                "marketplace_id": context.get("marketplace_id"),
            }
        elif "product-id" in record:
            return {
                "ASIN": record["product-id"],
                "marketplace_id": context.get("marketplace_id"),
            }
        else:
            return []

    @backoff.on_exception(
        backoff.expo,
        (Exception),
        max_tries=10,
        factor=3,
    )
    # @timeout(15)
    def get_records(self, context: Optional[dict]) -> Iterable[dict]:
        try:
            # Leaving it here for EU marketplaces reference.
            eu_marketplaces = [
                "ES",
                "UK",
                "BE",
                "GB",
                "FR",
                "NL",
                "DE",
                "IT",
                "SE",
                "ZA",
                "PL",
                "EG",
                "TR",
                "SA",
                "AE",
                "IN",
            ]
            start_date = self.get_starting_timestamp(context) or datetime(2005, 1, 1)
            end_date = None
            if self.config.get("start_date"):
                start_date = parse(self.config.get("start_date"))

            start_date = start_date.strftime("%Y-%m-%dT00:00:00")
            report_types = ["GET_AFN_INVENTORY_DATA_BY_COUNTRY"]
            processing_status = self.config.get("processing_status")
            # Get list of valid marketplaces
            marketplaces = self.get_valid_marketplaces()
            common_marketplaces = list(set(marketplaces).intersection(eu_marketplaces))
            marketplace_id = None
            if len(common_marketplaces) > 0:
                marketplace_id = common_marketplaces[0]

            if marketplace_id in eu_marketplaces:
                report = self.get_sp_reports(marketplace_id=marketplace_id)

                items = report.get_reports(
                    reportTypes=report_types,
                    processingStatuses=processing_status,
                    dataStartTime=start_date,
                ).payload

                if not items["reports"]:
                    reports = self.create_report(
                        start_date,
                        report,
                        end_date,
                        "GET_AFN_INVENTORY_DATA_BY_COUNTRY",
                    )
                    for row in reports:
                        yield row

                # If reports are form loop through, download documents and populate the data.txt
                for row in items["reports"]:
                    reports = self.check_report(row["reportId"], report)
                    for report_row in reports:
                        if context is not None:
                            report_row.update(
                                {marketplace_id: context.get("marketplace_id")}
                            )
                        yield report_row

        except Exception as e:
            raise InvalidResponse(e)


class SalesTrafficReportStream(AmazonSellerStream):
    """Define custom stream."""

    name = "sales_traffic_report"
    primary_keys = None
    replication_key = "report_end_date"
    report_id = None
    document_id = None
    schema = th.PropertiesList(
        th.Property("reportId", th.StringType),
        th.Property(
            "reportSpecification", th.CustomType({"type": ["object", "string"]})
        ),
        th.Property(
            "salesAndTrafficByDate", th.CustomType({"type": ["array", "string"]})
        ),
        th.Property(
            "salesAndTrafficByAsin", th.CustomType({"type": ["array", "string"]})
        ),
        th.Property("report_end_date", th.DateTimeType),
    ).to_dict()

    @backoff.on_exception(
        backoff.expo,
        (Exception),
        max_tries=10,
        factor=5,
    )
    # @timeout(15)
    def get_records(self, context: Optional[dict]) -> Iterable[dict]:
        try:
            start_date = self.get_starting_timestamp(context)
            if start_date:
                # Remove timezone info from replication date so we can compare it with other dates.
                start_date = start_date.replace(tzinfo=None)
            end_date = None
            if self.config.get("start_date") and not start_date:
                start_date = parse(self.config.get("start_date"))
            # We can only do look back of maximum two years in this report type
            days_look_back = 730
            current_date = datetime.now()
            minimum_start_date = current_date - timedelta(days=days_look_back)
            if start_date < minimum_start_date:
                # Reset start date to days limit if it is greater than days_look_back days
                start_date = current_date - timedelta(days=days_look_back)

            end_date = start_date + timedelta(days=14)
            report_type = "GET_SALES_AND_TRAFFIC_REPORT"
            report_types = [report_type]
            processing_status = self.config.get("processing_status")
            # Get list of valid marketplaces

            marketplace_id = None
            if context is not None:
                marketplace_id = context.get("marketplace_id")

            report = self.get_sp_reports(marketplace_id=marketplace_id)
            while start_date <= current_date:
                start_date_f = start_date.strftime("%Y-%m-%dT00:00:00")
                end_date_f = end_date.strftime("%Y-%m-%dT23:59:59")
                items = self.get_reports_list(
                    report, report_types, processing_status, start_date_f, end_date_f
                )

                if not items["reports"]:
                    reports = self.create_report(
                        start_date_f,
                        report,
                        end_date_f,
                        report_type,
                        # reportOptions={"reportPeriod": "DAY","sellingProgram": "RETAIL","distributorView": "MANUFACTURING"},
                        report_format_type="json",
                    )
                    for row in reports:
                        row.update({"report_end_date": end_date.isoformat()})
                        yield row

                # If reports are form loop through, download documents and populate the data.txt
                for row in items["reports"]:
                    reports = self.check_report(row["reportId"], report, "json")
                    for report_row in reports:
                        report_row.update({"report_end_date": end_date.isoformat()})
                        yield report_row
                # Move to the next time period
                start_date = end_date + timedelta(days=1)
                end_date += timedelta(days=14)
                do_something = ""

        except Exception as e:
            raise InvalidResponse(e)


class FBAInventoryLedgerDetailedReportStream(AmazonSellerStream):
    """Define custom stream."""

    name = "fba_inventory_ledger_detailed"
    primary_keys = None
    replication_key = "Date"
    report_id = None
    document_id = None
    schema = th.PropertiesList(
        th.Property("Date", th.DateTimeType),
        th.Property("FNSKU", th.StringType),
        th.Property("ASIN", th.StringType),
        th.Property("MSKU", th.StringType),
        th.Property("Title", th.StringType),
        th.Property("Event Type", th.StringType),
        th.Property("Reference ID", th.StringType),
        th.Property("Quantity", th.StringType),
        th.Property("Fulfillment Center", th.StringType),
        th.Property("Disposition", th.StringType),
        th.Property("Reason", th.StringType),
        th.Property("Country", th.StringType),
        th.Property("Reconciled Quantity", th.StringType),
        th.Property("Unreconciled Quantity", th.StringType),
        th.Property("Date and Time", th.DateTimeType),
        th.Property("report_end_date", th.DateTimeType),
    ).to_dict()

    @backoff.on_exception(
        backoff.expo,
        (Exception),
        max_tries=10,
        factor=5,
    )
    # @timeout(15)
    def get_records(self, context: Optional[dict]) -> Iterable[dict]:
        try:
            start_date = self.get_starting_timestamp(context)
            if start_date:
                # Remove timezone info from replication date so we can compare it with other dates.
                start_date = start_date.replace(tzinfo=None)
            end_date = None
            if self.config.get("start_date") and not start_date:
                start_date = parse(self.config.get("start_date"))
            # We can only do look back of maximum two years in this report type
            months_lookback = 18
            current_date = datetime.now()
            minimum_start_date = current_date - relativedelta(months=months_lookback)
            if start_date < minimum_start_date:
                # Reset start date to days limit if it is greater than days_look_back days
                start_date = current_date - relativedelta(months=months_lookback)

            end_date = current_date
            report_type = "GET_LEDGER_DETAIL_VIEW_DATA"
            report_types = [report_type]
            processing_status = self.config.get("processing_status")
            # Get list of valid marketplaces

            marketplace_id = None
            if context is not None:
                marketplace_id = context.get("marketplace_id")

            report = self.get_sp_reports(marketplace_id=marketplace_id)
            start_date_f = start_date.strftime("%Y-%m-%dT00:00:00")
            end_date_f = end_date.strftime("%Y-%m-%dT23:59:59")
            items = self.get_reports_list(
                report, report_types, processing_status, start_date_f, end_date_f
            )

            if not items["reports"]:
                reports = self.create_report(
                    start_date_f,
                    report,
                    end_date_f,
                    report_type,
                    reportOptions={"eventType": "Adjustments"},
                )
                for row in reports:
                    row.update({"report_end_date": end_date.isoformat()})
                    if "Date" in row:
                        date_object = datetime.strptime(row["Date"], "%m/%d/%Y")
                        row["Date"] = date_object.date().isoformat()
                    yield row

            # If reports are form loop through, download documents and populate the data.txt
            for row in items["reports"]:
                reports = self.check_report(row["reportId"], report, "json")
                for report_row in reports:
                    if "Date" in report_row:
                        date_object = datetime.strptime(report_row["Date"], "%m/%d/%Y")
                        report_row["Date"] = date_object.date().isoformat()
                    
                    report_row.update({"report_end_date": end_date.isoformat()})
                    yield report_row

        except Exception as e:
            raise InvalidResponse(e)


class FBACustomerShipmentSalesReportStream(AmazonSellerStream):
    """Define custom stream."""

    name = "fba_customer_shipment_sales"
    primary_keys = None
    replication_key = "shipment-date"
    report_id = None
    document_id = None
    correct_end_date_minus_days = 2 #EU has upto 24 hour delay in updates
    schema = th.PropertiesList(
        th.Property("shipment-date", th.DateTimeType),
        th.Property("sku", th.StringType),
        th.Property("fnsku", th.StringType),
        th.Property("asin", th.StringType),
        th.Property("fulfillment-center-id", th.StringType),
        th.Property("quantity", th.StringType),
        th.Property("amazon-order-id", th.StringType),
        th.Property("currency", th.StringType),
        th.Property("item-price-per-unit", th.StringType),
        th.Property("shipping-price", th.StringType),
        th.Property("gift-wrap-price", th.StringType),
        th.Property("ship-city", th.StringType),
        th.Property("ship-state", th.StringType),
        th.Property("ship-postal-code", th.StringType),
    ).to_dict()

    def correct_end_date(self, end_date, start_date, current_date):
        if end_date > current_date:
            # If end_date is greater than today then fetch report for yesterday.
            end_date = current_date - timedelta(days=self.correct_end_date_minus_days)

        if end_date <= start_date:
            end_date = start_date
        return end_date

    @backoff.on_exception(
        backoff.expo,
        (Exception),
        max_tries=10,
        factor=5,
    )
    # @timeout(15)
    def get_records(self, context: Optional[dict]) -> Iterable[dict]:
        try:
            start_date = self.get_starting_timestamp(context)
            if start_date:
                # Remove timezone info from replication date so we can compare it with other dates.
                start_date = start_date.replace(tzinfo=None)
            end_date = None
            if self.config.get("start_date") and not start_date:
                start_date = parse(self.config.get("start_date"))
            # We can only do look back of maximum two years in this report type
            days_look_back = 545  # Few days less than 18 months
            current_date = datetime.now()
            minimum_start_date = current_date - timedelta(days=days_look_back)
            if start_date < minimum_start_date:
                # Reset start date to days limit if it is greater than days_look_back days
                start_date = current_date - timedelta(days=days_look_back)

            end_date = start_date + timedelta(days=30)
            end_date = self.correct_end_date(end_date, start_date, current_date)
            report_type = "GET_FBA_FULFILLMENT_CUSTOMER_SHIPMENT_SALES_DATA"
            report_types = [report_type]
            processing_status = self.config.get("processing_status")
            # Get list of valid marketplaces

            marketplace_id = None
            if context is not None:
                marketplace_id = context.get("marketplace_id")

            report = self.get_sp_reports(marketplace_id=marketplace_id)
            while start_date <= current_date:
                start_date_f = start_date.strftime("%Y-%m-%dT00:00:00")
                end_date_f = end_date.strftime("%Y-%m-%dT23:59:59")
                items = self.get_reports_list(
                    report, report_types, processing_status, start_date_f, end_date_f
                )

                if not items["reports"]:
                    reports = self.create_report(
                        start_date_f,
                        report,
                        end_date_f,
                        report_type,
                    )
                    if not reports:
                        return None
                    for row in reports:
                        row.update({"report_end_date": end_date.isoformat()})
                        yield row

                # If reports are form loop through, download documents and populate the data.txt
                for row in items["reports"]:
                    reports = self.check_report(row["reportId"], report, "json")
                    for report_row in reports:
                        report_row.update({"report_end_date": end_date.isoformat()})
                        yield report_row
                # Move to the next time period
                start_date = end_date + timedelta(days=1)
                end_date += timedelta(days=30)
                end_date = self.correct_end_date(end_date, start_date, current_date)
                # According to Amazon, spamming bad is, wait for it, good you should - Yoda's lesson of the day!
                time.sleep(60)

        except Exception as e:
            raise InvalidResponse(e)
