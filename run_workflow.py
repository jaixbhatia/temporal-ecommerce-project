"""
Test runner for Temporal e-commerce workflows.
Demonstrates OrderWorkflow execution and signal handling.
"""
import asyncio
import sys
import os
import uuid
import time
from datetime import timedelta

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from temporalio.client import Client
from workflows import OrderWorkflow

async def main():
    """Test the OrderWorkflow execution."""
    print("Testing OrderWorkflow Execution")
    print("-" * 50)
    
    # Create client connected to server at the given address
    client = await Client.connect("localhost:7233")
    
    # Generate test IDs
    order_id = f"order-{uuid.uuid4().hex[:8]}"
    payment_id = f"payment-{uuid.uuid4().hex[:8]}"
    
    print(f"Order ID: {order_id}")
    print(f"Payment ID: {payment_id}")
    print()
    
    try:
        # Execute the OrderWorkflow
        print("Starting OrderWorkflow...")
        workflow_start_time = time.time()
        
        handle = await client.start_workflow(
            OrderWorkflow.run,
            args=[order_id, payment_id],
            id=f"order-workflow-{order_id}",
            task_queue="order-tq"
        )
        
        print(f"Workflow started with ID: {handle.id}")
        print("Waiting for workflow completion...")
        
        # Wait for workflow completion
        result = await handle.result()
        
        workflow_total_time = time.time() - workflow_start_time
        print("Workflow completed successfully!")
        print(f"Total execution time: {workflow_total_time:.3f} seconds")
        print(f"Result: {result}")
        
        # Check if we met the 15-second requirement
        if workflow_total_time <= 15.0:
            print("Workflow completed within 15 seconds requirement!")
        else:
            print(f"Workflow took {workflow_total_time:.3f}s (target: ≤15s)")
        
    except Exception as e:
        print(f"Workflow failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nTest stopped by user")
        sys.exit(1)
    except Exception as e:
        print(f"Test error: {e}")
        sys.exit(1)
