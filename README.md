# Temporal E-commerce Workflow

A robust e-commerce order processing system built with Temporal, featuring:
- Parent-child workflow architecture
- Retries and timeouts
- Signals for order cancellation and address updates
- Idempotent payment processing
- PostgreSQL persistence
- FastAPI-based REST API

## Quick Start

1. **Start Infrastructure & API**
   ```bash
   chmod +x scripts/start_all.sh
   ./scripts/start_all.sh
   ```
   This will:
   - Start Temporal and PostgreSQL via Docker Compose
   - Start the Temporal worker
   - Start the FastAPI server

2. **Access API Documentation**
   - Open http://localhost:8000/docs in your browser
   - Interactive Swagger UI documentation for all endpoints

## API Endpoints

### Start a New Order
```bash
curl -X POST http://localhost:8000/orders/order-123/start \
  -H "Content-Type: application/json" \
  -d '{"payment_id": "payment-456"}'
```

### Cancel an Order
```bash
curl -X POST http://localhost:8000/orders/order-123/signals/cancel
```

### Update Shipping Address
```bash
curl -X POST http://localhost:8000/orders/order-123/signals/update-address \
  -H "Content-Type: application/json" \
  -d '{
    "street": "123 Main St",
    "city": "San Francisco",
    "state": "CA",
    "zip_code": "94105"
  }'
```

### Check Order Status
```bash
curl http://localhost:8000/orders/order-123/status
```

## Database Schema

The system uses PostgreSQL with three main tables:

1. **orders**
   - Primary persistence for order state
   - Tracks order status and shipping details
   - Used for idempotency checks

2. **payments**
   - Strict idempotency for payment processing
   - Uses payment_id as idempotency key
   - UPSERT patterns prevent double-charging

3. **events**
   - Audit log of all state transitions
   - Foreign key to orders for data consistency
   - Helps with debugging and observability

Database migrations are managed with SQLAlchemy and can be found in `migrations/`.

## Development

1. **Setup Virtual Environment**
   ```bash
   python -m venv env
   source env/bin/activate  # or `env\Scripts\activate` on Windows
   pip install -r requirements.txt
   ```

2. **Run Tests**
   ```bash
   pytest tests/
   ```

3. **Manual Testing**
   ```bash
   # Terminal 1: Start infrastructure
   ./scripts/start_all.sh

   # Terminal 2: Test workflow
   python run_workflow.py
   ```

## Architecture

1. **Parent Workflow (`OrderWorkflow`)**
   - Manages overall order lifecycle
   - Handles payment processing
   - Spawns child workflow for shipping
   - Responds to cancel/update signals

2. **Child Workflow (`ShippingWorkflow`)**
   - Runs on separate task queue
   - Handles package preparation
   - Manages carrier dispatch
   - Independent retry policies

3. **Activities**
   - Small, focused units of work
   - Aggressive timeouts (1-5 seconds)
   - Automatic retries on failure
   - Idempotent database operations

4. **API Layer**
   - RESTful endpoints via FastAPI
   - Swagger UI documentation
   - Async/await throughout
   - Error handling and validation

## Performance

The entire workflow is designed to complete within 15 seconds:
- Aggressive activity timeouts (1s)
- Fast retry intervals (0.1s)
- No exponential backoff
- Parallel task queues
- Optimized database operations

## Observability

1. **Workflow State**
   - Query current step via API
   - Track order status in database
   - Monitor event log for transitions

2. **Logging**
   - Activity success/failure
   - Retry attempts
   - Timing information
   - Database operations

3. **Temporal UI**
   - Open http://localhost:8233
   - View workflow executions
   - Inspect activity details
   - Send signals manually

## Security Notes

1. **Payment Processing**
   - Strict idempotency via database
   - Double-charge prevention
   - Transaction isolation

2. **Data Consistency**
   - Foreign key constraints
   - Transaction boundaries
   - Event logging

3. **API Security**
   - Input validation
   - Error handling
   - Rate limiting (TODO)

## Future Improvements

1. **Features**
   - Authentication/Authorization
   - Rate limiting
   - Metrics collection
   - More payment methods

2. **Operations**
   - Monitoring setup
   - Alerting
   - Backup/restore
   - Production deployment guide