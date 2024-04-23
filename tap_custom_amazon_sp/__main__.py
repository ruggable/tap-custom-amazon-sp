"""custom-amazon-sp entry point."""

from __future__ import annotations

from tap_custom_amazon_sp.tap import TapAmazonSeller

TapAmazonSeller.cli()
