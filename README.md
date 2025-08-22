# Temporal E-commerce Workflow

## Demo

https://github.com/user-attachments/assets/17f79f71-c25f-4b09-9829-6528d1623459





## How to start Temporal server and database:

**Option 1: Manual setup**
```bash
docker-compose up -d
```

**Option 2: Use convenience script (recommended)**
```bash
chmod +x scripts/start_all.sh
./scripts/start_all.sh
```
This script automatically:
- Starts Temporal and PostgreSQL via Docker
- Activates Python virtual environment  
- Starts the Temporal worker in background
- Launches FastAPI server with Swagger UI

**Access Swagger UI:**
Visit http://localhost:8000/docs to trigger workflows, send signals, and query state via interactive API documentation.

**Monitor Performance:**
When you make API calls, you'll see detailed timing logs in the terminal showing how long each step takes and overall timing

## How to run workers and trigger workflow:

First source/env/activate and make sure you have python installed locally

```bash
# Start workers
python run_worker.py

# Trigger workflow via API
curl -X POST http://localhost:8000/orders/order-123/start -H "Content-Type: application/json" -d '{"payment_id": "payment-456"}'

# Or via Python script
python run_workflow.py
```

## How to send signals and query/inspect state:
```bash
# Send signals
curl -X POST http://localhost:8000/orders/order-123/signals/cancel
curl -X POST http://localhost:8000/orders/order-123/signals/update-address -H "Content-Type: application/json" -d '{"street": "123 Main St"}'

# Query state
curl http://localhost:8000/orders/order-123/status
```

## Schema/migrations and persistence rationale:

**Database Tables:**
- **orders**: Primary state persistence for order lifecycle
- **payments**: Idempotency key prevents double-charging  
- **events**: Audit trail for debugging and compliance

**Persistence Design:**
- Foreign keys ensure data consistency
- UPSERT patterns prevent duplicate payments
- Event sourcing for complete audit trail

## Tests and how to run them:
```bash
pytest tests/
```
