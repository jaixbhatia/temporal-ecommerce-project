"""
FastAPI-based API for the e-commerce workflow.
Provides endpoints to start workflows, send signals, and query state.
"""
import uuid
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from temporalio.client import Client
from workflows import OrderWorkflow

app = FastAPI(
    title="E-commerce Workflow API",
    description="API to manage Temporal e-commerce workflows",
    version="1.0.0"
)

# Request/Response Models
class StartWorkflowRequest(BaseModel):
    payment_id: Optional[str] = None  # Optional - we'll generate if not provided

class AddressUpdateRequest(BaseModel):
    street: str
    city: str
    state: str
    postal_code: str
    country: str

class WorkflowResponse(BaseModel):
    workflow_id: str
    status: str
    message: str

# Cached Temporal client
_temporal_client: Optional[Client] = None

async def get_temporal_client() -> Client:
    """Get or create Temporal client."""
    global _temporal_client
    if _temporal_client is None:
        _temporal_client = await Client.connect("localhost:7233")
    return _temporal_client

@app.post("/orders/{order_id}/start", response_model=WorkflowResponse)
async def start_workflow(order_id: str, request: StartWorkflowRequest):
    """Start a new OrderWorkflow for the given order_id."""
    try:
        client = await get_temporal_client()
        
        # Generate payment_id if not provided
        payment_id = request.payment_id or f"payment-{uuid.uuid4().hex[:8]}"
        workflow_id = f"order-workflow-{order_id}"
        
        # Start workflow
        handle = await client.start_workflow(
            OrderWorkflow.run,
            args=[order_id, payment_id],
            id=workflow_id,
            task_queue="order-tq"
        )
        
        return WorkflowResponse(
            workflow_id=workflow_id,
            status="started",
            message=f"Workflow started with payment_id: {payment_id}"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/orders/{order_id}/signals/cancel", response_model=WorkflowResponse)
async def cancel_order(order_id: str):
    """Send cancel signal to an OrderWorkflow."""
    try:
        client = await get_temporal_client()
        workflow_id = f"order-workflow-{order_id}"
        
        # Get workflow handle
        handle = client.get_workflow_handle(workflow_id)
        
        # Send cancel signal
        await handle.signal(OrderWorkflow.cancel_order)
        
        return WorkflowResponse(
            workflow_id=workflow_id,
            status="cancelled",
            message="Cancel signal sent successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/orders/{order_id}/status")
async def get_workflow_status(order_id: str):
    """Query workflow status."""
    try:
        client = await get_temporal_client()
        workflow_id = f"order-workflow-{order_id}"
        
        # Get workflow handle
        handle = client.get_workflow_handle(workflow_id)
        
        # Query workflow status
        status = await handle.query(OrderWorkflow.get_status)
        
        return status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/orders/{order_id}/address", response_model=WorkflowResponse, 
    summary="Update Order Address",
    description="Updates the shipping address for an existing order workflow",
    responses={
        200: {
            "description": "Address updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "workflow_id": "order-workflow-123",
                        "status": "address_updated",
                        "message": "Shipping address updated successfully"
                    }
                }
            }
        },
        404: {"description": "Order workflow not found"},
        500: {"description": "Internal server error"}
    })
async def update_address(order_id: str, address: AddressUpdateRequest):
    """
    Update the shipping address for an order.
    
    Parameters:
    - order_id: Unique identifier for the order
    - address: New shipping address details
    
    The address update will be sent as a signal to the running workflow.
    """
    try:
        client = await get_temporal_client()
        workflow_id = f"order-workflow-{order_id}"
        
        # Get workflow handle
        handle = client.get_workflow_handle(workflow_id)
        
        # Send address update signal
        await handle.signal(OrderWorkflow.update_address, address.dict())
        
        return WorkflowResponse(
            workflow_id=workflow_id,
            status="address_updated",
            message="Shipping address updated successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
