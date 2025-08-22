"""
Temporal activities that call business functions.
Keep activities small: parameter unpacking, await the function, return its result.
"""
import logging
import asyncio
from temporalio import activity
from typing import Dict, Any
from business_functions import (
    order_received, order_validated, payment_charged,
    package_prepared, carrier_dispatched
)

async def handle_flaky_call(func, *args, **kwargs):
    """Wrapper to handle flaky calls with clean logging."""
    try:
        return await func(*args, **kwargs)
    except RuntimeError as e:
        if "Forced failure for testing" in str(e):
            logging.info("Simulated failure (immediate retry)")
        raise
    except asyncio.CancelledError:
        logging.info("Simulated timeout (will retry)")
        raise

@activity.defn
async def receive_order_activity(order_id: str) -> Dict[str, Any]:
    """Simple activity that calls the business function."""
    return await handle_flaky_call(order_received, order_id)

@activity.defn
async def validate_order_activity(order: Dict[str, Any]) -> bool:
    """Simple activity that calls the business function."""
    return await handle_flaky_call(order_validated, order)

@activity.defn
async def charge_payment_activity(order: Dict[str, Any], payment_id: str) -> Dict[str, Any]:
    """Simple activity that calls the business function."""
    return await handle_flaky_call(payment_charged, order, payment_id)

@activity.defn
async def prepare_package_activity(order: Dict[str, Any]) -> str:
    """Simple activity that calls the business function."""
    return await handle_flaky_call(package_prepared, order)

@activity.defn
async def dispatch_carrier_activity(order: Dict[str, Any]) -> str:
    """Simple activity that calls the business function."""
    return await handle_flaky_call(carrier_dispatched, order)