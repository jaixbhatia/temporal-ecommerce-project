"""
Temporal workflows for e-commerce order processing.
Includes OrderWorkflow (parent) and ShippingWorkflow (child) with signals, timers, and separate task queues.
"""
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from typing import Dict, Any, Optional

# Import activities, passing them through the sandbox without reloading the module
with workflow.unsafe.imports_passed_through():
    from activities import (
        receive_order_activity, validate_order_activity, charge_payment_activity,
        prepare_package_activity, dispatch_carrier_activity
    )

@workflow.defn
class OrderWorkflow:
    """Parent workflow that manages the entire order lifecycle."""
    
    def __init__(self):
        self._order_id: str = ""
        self._payment_id: str = ""
        self._order_data: Dict[str, Any] = {}
        self._shipping_address: Dict[str, Any] = {}
        self._is_cancelled: bool = False
        self._current_step: str = "initialized"
    
    @workflow.signal
    def cancel_order(self) -> None:
        """Signal to cancel the order before shipment."""
        self._is_cancelled = True
        self._current_step = "cancelled"
        workflow.logger.info(f"Order {self._order_id} cancelled")
    
    @workflow.signal
    def update_address(self, address: Dict[str, Any]) -> None:
        """Signal to update shipping address prior to dispatch."""
        self._shipping_address = address
        self._current_step = "address_updated"
    
    @workflow.query
    def get_status(self) -> Dict[str, Any]:
        """Query to get current workflow status."""
        return {
            "order_id": self._order_id,
            "current_step": self._current_step,
            "is_cancelled": self._is_cancelled,
            "shipping_address": self._shipping_address,
            "order_data": self._order_data
        }
    
    @workflow.run
    async def run(self, order_id: str, payment_id: str) -> Dict[str, Any]:
        """Main workflow execution with 15-second time constraint."""
        start_time = workflow.now()
        self._order_id = order_id
        self._payment_id = payment_id
        self._current_step = "started"
        workflow.logger.info(f"[WORKFLOW] Starting workflow for order {order_id}")
        
        #  agressive retries
        retry_policy = RetryPolicy(
            initial_interval=timedelta(milliseconds=1),  
            maximum_interval=timedelta(milliseconds=10),
            backoff_coefficient=1.0,                    # No backoff 
        )
        
        try:
            # Step 1: Receive Order
            self._current_step = "receiving_order"
            self._order_data = await workflow.execute_activity(
                receive_order_activity,
                args=[order_id],
                start_to_close_timeout=timedelta(milliseconds=100),  # Very aggressive timeout
                retry_policy=retry_policy
            )
            
            # Check for cancellation
            if self._is_cancelled:
                workflow.logger.info(f"Order {order_id} cancelled after receiving")
                return {"status": "cancelled", "step": "order_received"}
            
            # Step 2: Validate Order
            self._current_step = "validating_order"
            validation_result = await workflow.execute_activity(
                validate_order_activity,
                args=[self._order_data],
                start_to_close_timeout=timedelta(milliseconds=100),
                retry_policy=retry_policy
            )
            
            if not validation_result:
                raise ValueError("Order validation failed")
            
            # Check for cancellation
            if self._is_cancelled:
                workflow.logger.info(f"Order {order_id} cancelled after validation")
                return {"status": "cancelled", "step": "order_validated"}
            
            # Step 3: Timer for Manual Review (simulated)
            self._current_step = "manual_review"
            await workflow.sleep(timedelta(milliseconds=100))  # Quick simulated review
            
            # Check for cancellation
            if self._is_cancelled:
                workflow.logger.info(f"Order {order_id} cancelled after manual review")
                return {"status": "cancelled", "step": "manual_review"}
            
            # Step 4: Charge Payment
            self._current_step = "charging_payment"
            payment_result = await workflow.execute_activity(
                charge_payment_activity,
                args=[self._order_data, payment_id],
                start_to_close_timeout=timedelta(milliseconds=100),
                retry_policy=retry_policy
            )
            
            if payment_result.get("status") != "charged":
                raise RuntimeError("Payment failed")
            
            # Check for cancellation
            if self._is_cancelled:
                workflow.logger.info(f"Order {order_id} cancelled after payment")
                return {"status": "cancelled", "step": "payment_charged"}
            
            # Step 5: Start ShippingWorkflow as Child Workflow
            self._current_step = "starting_shipping"
            
            # Start shipping workflow
            if self._is_cancelled:
                workflow.logger.info(f"Order {order_id} cancelled before shipping starts")
                return {"status": "cancelled", "step": "shipping_started"}
            
            # Execute child workflow
            shipping_result = await workflow.execute_child_workflow(
                ShippingWorkflow.run,
                args=[self._order_data],
                id=f"shipping-{order_id}",
                task_queue="shipping-tq"  # Separate task queue
            )
            
            self._current_step = "completed"
            end_time = workflow.now()
            total_time = (end_time - start_time).total_seconds()
            
            workflow.logger.info(f"WORKFLOW] Order {order_id} completed successfully in {total_time:.2f}s")
            
            # Check if we met the 15-second requirement
            if total_time <= 15.0:
                workflow.logger.info(f"[WORKFLOW] Met 15-second requirement ({total_time:.2f}s)")
            else:
                workflow.logger.warn(f"[WORKFLOW] Exceeded 15-second target: {total_time:.2f}s")
            
            return {
                "status": "completed",
                "order_id": order_id,
                "payment_result": payment_result,
                "shipping_result": shipping_result,
                "execution_time": total_time
            }
            
        except Exception as e:
            self._current_step = "failed"
            workflow.logger.error(f"Order {order_id} failed: {str(e)}")
            raise e

@workflow.defn
class ShippingWorkflow:
    """Child workflow for shipping operations on separate task queue."""
    
    def __init__(self):
        self._order_data: Dict[str, Any] = {}
        self._dispatch_failed: bool = False
        self._failure_reason: str = ""
    
    @workflow.run
    async def run(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute shipping workflow with retry logic."""
        self._order_data = order_data
        order_id = order_data.get("order_id", "unknown")
        
        retry_policy = RetryPolicy(
            initial_interval=timedelta(milliseconds=1),  # Start retrying almost instantly
            maximum_interval=timedelta(milliseconds=10), # Keep retries very fast
            backoff_coefficient=1.0                     # No backoff
        )
        
        try:
            # Step 1: Prepare Package
            workflow.logger.info(f"Starting package preparation for order {order_id}")
            package_status = await workflow.execute_activity(
                prepare_package_activity,
                args=[order_data],
                start_to_close_timeout=timedelta(milliseconds=100),  # Very aggressive timeout
                retry_policy=retry_policy
            )
            
            # Step 2: Dispatch Carrier
            workflow.logger.info(f"Starting carrier dispatch for order {order_id}")
            dispatch_status = await workflow.execute_activity(
                dispatch_carrier_activity,
                args=[order_data],
                start_to_close_timeout=timedelta(milliseconds=100),  # Very aggressive timeout
                retry_policy=retry_policy
            )
            
            workflow.logger.info(f"Shipping completed for order {order_id}")
            return {
                "status": "shipped",
                "package_status": package_status,
                "dispatch_status": dispatch_status
            }
            
        except Exception as e:
            self._dispatch_failed = True
            self._failure_reason = str(e)
            workflow.logger.error(f"Shipping failed for order {order_id}: {str(e)}")
            raise RuntimeError(f"Shipping failed: {str(e)}")