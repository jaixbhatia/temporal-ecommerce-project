"""
Temporal workers for e-commerce order processing.
Includes order worker and shipping worker on separate task queues.
"""
import asyncio
import sys
import os
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
# show workflow logs but hide noise
logging.getLogger('temporalio').setLevel(logging.ERROR)
logging.getLogger('temporalio.worker').setLevel(logging.ERROR)
logging.getLogger('temporalio.client').setLevel(logging.ERROR)  
logging.getLogger('temporalio.activity').setLevel(logging.ERROR)  
logging.getLogger('temporalio.workflow').setLevel(logging.INFO)  # Show workflow logs
logging.getLogger('temporalio.worker._activity').setLevel(logging.ERROR)  

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker

from activities import (
    receive_order_activity, validate_order_activity, charge_payment_activity,
    prepare_package_activity, dispatch_carrier_activity
)
from workflows import OrderWorkflow, ShippingWorkflow

async def run_order_worker():
    """Run the order processing worker."""
    client = await Client.connect("localhost:7233", namespace="default")
    
    worker = Worker(
        client,
        task_queue="order-tq",
        workflows=[OrderWorkflow],
        activities=[
            receive_order_activity,
            validate_order_activity,
            charge_payment_activity
        ]
    )
    
    print("Starting Order Worker on task queue: order-tq")
    await worker.run()

async def run_shipping_worker():
    """Run the shipping worker on separate task queue."""
    client = await Client.connect("localhost:7233", namespace="default")
    
    worker = Worker(
        client,
        task_queue="shipping-tq",
        workflows=[ShippingWorkflow],
        activities=[
            prepare_package_activity,
            dispatch_carrier_activity
        ]
    )
    
    print("Starting Shipping Worker on task queue: shipping-tq")
    await worker.run()

async def main():
    """Run both workers concurrently."""
    print("Starting Temporal E-commerce Workers...")
    
    await asyncio.gather(
        run_order_worker(),
        run_shipping_worker()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nWorkers stopped by user")
    except Exception as e:
        print(f"Worker error: {e}")
        sys.exit(1)