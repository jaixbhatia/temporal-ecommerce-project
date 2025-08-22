"""
Business functions that implement the actual database operations.
These functions are called by the activities and handle the database work.
"""
import asyncio
import random
import logging
import time
from typing import Dict, Any
from database import get_db, Order, Payment, Event
from sqlalchemy import text

# Reduce SQLAlchemy logging noise - show errors but not all SQL
logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)
logging.getLogger('sqlalchemy.pool').setLevel(logging.ERROR)
logging.getLogger('sqlalchemy.dialects').setLevel(logging.ERROR)
logging.getLogger('sqlalchemy.orm').setLevel(logging.ERROR)

async def flaky_call() -> None:
    """Either raise an error or sleep long enough to trigger an activity timeout."""
    rand_num = random.random()
    if rand_num < 0.33:
        raise RuntimeError("Forced failure for testing")
    
    if rand_num < 0.67:
        await asyncio.sleep(300)  # Expect the activity layer to time out before this completes

async def order_received(order_id: str) -> Dict[str, Any]:
    """Receive a new order and store it in the database."""
    start_time = time.time()
    await flaky_call()
    
    # First transaction: Create order
    async with get_db() as session:
        # check if order exists, return it
        existing_order = await session.get(Order, order_id)
        if existing_order:
            elapsed = time.time() - start_time
            logging.info(f"Order {order_id} already exists (took {elapsed:.3f}s)")
            return {"order_id": order_id, "items": [{"sku": "ABC", "qty": 1}]}
        
        # Create new order
        order = Order(
            id=order_id,
            state="received",
            address_json={"street": "Default Address", "city": "Default City"}
        )
        session.add(order)
        await session.commit()
    
    # Second transaction: Create event (now that order exists)
    async with get_db() as session:
        event = Event(
            order_id=order_id,
            type="order_received",
            payload_json={"order_id": order_id}
        )
        session.add(event)
        await session.commit()
    
    elapsed = time.time() - start_time
    logging.info(f"Order {order_id} received and stored (took {elapsed:.3f}s)")
    return {"order_id": order_id, "items": [{"sku": "ABC", "qty": 1}]}

async def order_validated(order: Dict[str, Any]) -> bool:
    """Validate an order and update its status in the database."""
    start_time = time.time()
    await flaky_call()
    
    if not order.get("items"):
        raise ValueError("No items to validate")
    
    order_id = order.get("order_id")
    async with get_db() as session:
        # check if already validated, return success
        db_order = await session.get(Order, order_id)
        if not db_order:
            raise ValueError("Order not found")
            
        if db_order.state == "validated":
            elapsed = time.time() - start_time
            logging.info(f"Order {order_id} already validated (took {elapsed:.3f}s)")
            return True
            
        # Update state
        db_order.state = "validated"
        
        # Log event
        event = Event(
            order_id=order_id,
            type="order_validated",
            payload_json={"order_id": order_id, "status": "validated"}
        )
        session.add(event)
        
        await session.commit()
    
    elapsed = time.time() - start_time
    logging.info(f"Order {order_id} validated (took {elapsed:.3f}s)")
    return True

async def payment_charged(order: Dict[str, Any], payment_id: str) -> Dict[str, Any]:
    """Charge payment with strict idempotency guarantees."""
    start_time = time.time()
    await flaky_call()
    
    order_id = order.get("order_id")
    amount = sum(i.get("qty", 1) for i in order.get("items", []))
    
    async with get_db() as session:
        try:
            # Use payment_id as idempotency key
            # check if payment exists
            existing_payment = await session.get(Payment, payment_id)
            if existing_payment:
                elapsed = time.time() - start_time
                logging.info(f"Payment {payment_id} already processed (took {elapsed:.3f}s)")
                return {
                    "status": existing_payment.status,
                    "amount": float(existing_payment.amount)
                }
            
            result = await session.execute(
                text("""
                INSERT INTO payments (payment_id, order_id, status, amount)
                VALUES (:payment_id, :order_id, :status, :amount)
                ON CONFLICT (payment_id) DO NOTHING
                RETURNING payment_id
                """),
                {
                    "payment_id": payment_id,
                    "order_id": order_id,
                    "status": "charged",
                    "amount": amount
                }
            )
            
            if not result.scalar():
                # Fetch the existing payment
                existing_payment = await session.get(Payment, payment_id)
                elapsed = time.time() - start_time
                logging.info(f"Payment {payment_id} created by concurrent request (took {elapsed:.3f}s)")
                return {
                    "status": existing_payment.status,
                    "amount": float(existing_payment.amount)
                }
            
            # update order 
            db_order = await session.get(Order, order_id)
            if db_order:
                db_order.state = "paid"
            
            event = Event(
                order_id=order_id,
                type="payment_charged",
                payload_json={"payment_id": payment_id, "amount": amount}
            )
            session.add(event)
            
            await session.commit()
            elapsed = time.time() - start_time
            logging.info(f"Payment {payment_id} charged successfully (took {elapsed:.3f}s)")
            return {"status": "charged", "amount": amount}
            
        except Exception as e:
            raise e

async def package_prepared(order: Dict[str, Any]) -> str:
    """Mark package as prepared in the database."""
    start_time = time.time()
    await flaky_call()
    
    order_id = order.get("order_id")
    async with get_db() as session:
        result = await session.execute(
            text("SELECT 1 FROM events WHERE order_id = :order_id AND type = 'package_prepared'"),
            {"order_id": order_id}
        )
        if result.scalar():
            elapsed = time.time() - start_time
            logging.info(f"Package for order {order_id} already prepared (took {elapsed:.3f}s)")
            return "Package ready"
        
        event = Event(
            order_id=order_id,
            type="package_prepared",
            payload_json={"order_id": order_id, "status": "prepared"}
        )
        session.add(event)
        
        await session.commit()
    
    elapsed = time.time() - start_time
    logging.info(f"Package prepared for order {order_id} (took {elapsed:.3f}s)")
    return "Package ready"

async def carrier_dispatched(order: Dict[str, Any]) -> str:
    """Record carrier dispatch status in the database."""
    start_time = time.time()
    await flaky_call()
    
    order_id = order.get("order_id")
    async with get_db() as session:
        result = await session.execute(
            text("SELECT 1 FROM events WHERE order_id = :order_id AND type = 'carrier_dispatched'"),
            {"order_id": order_id}
        )
        if result.scalar():
            elapsed = time.time() - start_time
            logging.info(f"Carrier for order {order_id} already dispatched (took {elapsed:.3f}s)")
            return "Dispatched"
        
        event = Event(
            order_id=order_id,
            type="carrier_dispatched",
            payload_json={"order_id": order_id, "status": "dispatched"}
        )
        session.add(event)
        
        await session.commit()
    
    elapsed = time.time() - start_time
    logging.info(f"Carrier dispatched for order {order_id} (took {elapsed:.3f}s)")
    return "Dispatched"