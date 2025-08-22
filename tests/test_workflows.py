"""
Tests for Temporal workflows.
"""
import uuid
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from contextlib import asynccontextmanager
from temporalio.worker import Worker
from temporalio.testing import WorkflowEnvironment

# Mock database before importing anything that uses it
@asynccontextmanager
async def mock_db():
    session = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock(scalar=lambda: None))
    yield session

# Patch database connection before importing modules
with patch("database.connection.get_db", mock_db):
    from workflows import OrderWorkflow, ShippingWorkflow
    from activities import (
        receive_order_activity, validate_order_activity, charge_payment_activity,
        prepare_package_activity, dispatch_carrier_activity
    )

# Mock business function responses
async def mock_order_received(order_id: str):
    return {"order_id": order_id, "items": [{"id": "test-item", "quantity": 1}]}

async def mock_order_validated(order):
    return True

async def mock_payment_charged(order, payment_id):
    return {"status": "charged", "payment_id": payment_id, "amount": 100}

async def mock_package_prepared(order):
    return "Package ready"

async def mock_carrier_dispatched(order):
    return "Dispatched"

@pytest.mark.asyncio
async def test_execute_order_workflow():
    """Test basic order workflow execution."""
    task_queue_name = str(uuid.uuid4())
    
    # Patch business functions
    with patch("business_functions.order_received", mock_order_received), \
         patch("business_functions.order_validated", mock_order_validated), \
         patch("business_functions.payment_charged", mock_payment_charged), \
         patch("business_functions.package_prepared", mock_package_prepared), \
         patch("business_functions.carrier_dispatched", mock_carrier_dispatched):
        
        async with await WorkflowEnvironment.start_time_skipping() as env:
            async with Worker(
                env.client,
                task_queue=task_queue_name,
                workflows=[OrderWorkflow],
                activities=[
                    receive_order_activity,
                    validate_order_activity,
                    charge_payment_activity,
                    prepare_package_activity,
                    dispatch_carrier_activity
                ],
            ):
                result = await env.client.execute_workflow(
                    OrderWorkflow.run,
                    ["test-order-1", "test-payment-1"],
                    id=str(uuid.uuid4()),
                    task_queue=task_queue_name,
                )
                
                assert result["status"] == "completed"
                assert result["shipping_result"]["status"] == "shipped"

@pytest.mark.asyncio
async def test_execute_shipping_workflow():
    """Test basic shipping workflow execution."""
    task_queue_name = str(uuid.uuid4())
    order_data = {
        "order_id": "test-order-1",
        "items": [{"id": "item1", "quantity": 1}],
        "shipping_address": {
            "street": "123 Test St",
            "city": "Test City",
            "state": "TS",
            "postal_code": "12345"
        }
    }
    
    # Patch shipping-related business functions
    with patch("business_functions.package_prepared", mock_package_prepared), \
         patch("business_functions.carrier_dispatched", mock_carrier_dispatched):
        
        async with await WorkflowEnvironment.start_time_skipping() as env:
            async with Worker(
                env.client,
                task_queue=task_queue_name,
                workflows=[ShippingWorkflow],
                activities=[prepare_package_activity, dispatch_carrier_activity],
            ):
                result = await env.client.execute_workflow(
                    ShippingWorkflow.run,
                    [order_data],
                    id=str(uuid.uuid4()),
                    task_queue=task_queue_name,
                )
                
                assert result["status"] == "shipped"
