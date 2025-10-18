# Skadi Startup Checklist

## Pre-Flight Checks ✈️

### 1. Environment Setup
- [ ] Python 3.11+ installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file created from `.env.example`
- [ ] Database permissions (SQLite auto-creates, Postgres needs permissions)

### 2. Configuration Review
Edit `.env` and verify:
- [ ] `DATABASE_URL` points to correct database
- [ ] `DEFAULT_MODE` set to `advisory` for safety
- [ ] `GLOBAL_KILL_SWITCH` is `false`
- [ ] `SLA_LATENCY_MS` matches your requirements (default 250)
- [ ] `INLET_MAX_C` matches facility limits (default 28.0)
- [ ] Directory paths exist: `./data`, `./artifacts`, `./reports`

### 3. Test Backend Startup
```powershell
# Start server
uvicorn api.app:app --host 0.0.0.0 --port 8000

# Check health (in another terminal)
curl http://localhost:8000/health

# Expected: {"status": "healthy"}
```

- [ ] Server starts without errors
- [ ] Health endpoint responds
- [ ] Database initialized (check logs for "Database initialized successfully")
- [ ] Background tasks started (check logs for "All background tasks started")

### 4. API Smoke Test
```powershell
# Get root
curl http://localhost:8000/

# Get state overview
curl http://localhost:8000/state/overview

# Post test telemetry
curl -X POST http://localhost:8000/telemetry \
  -H "Content-Type: application/json" \
  -d '{\"samples\":[{\"ts\":\"2025-10-18T23:11:00Z\",\"rack_id\":\"R-C-07\",\"inlet_c\":24.8,\"outlet_c\":36.2,\"pdu_kw\":8.6,\"gpu_energy_j\":45250,\"tokens_ps\":9800,\"latency_p95_ms\":180,\"fan_rpm_pct\":62,\"pump_rpm_pct\":55,\"queue_depth\":42}]}'
```

- [ ] Root returns service info
- [ ] State overview returns (may be "no_data" initially)
- [ ] Telemetry POST succeeds

### 5. WebSocket Test
Use a WebSocket client (e.g., wscat, browser console, or Postman):
```javascript
// Browser console
const ws = new WebSocket('ws://localhost:8000/ws/events');
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

- [ ] WebSocket connects successfully
- [ ] Receives periodic updates

### 6. Demo Data Generation
```powershell
# Start demo generator (separate terminal)
python demo_generator.py --duration 5

# Verify data ingestion
curl http://localhost:8000/state/overview
```

- [ ] Generator starts and posts data
- [ ] State overview shows metrics after ~1 minute
- [ ] No errors in server logs

### 7. Demo Scenario Test
```powershell
# Start heat spike scenario
curl -X POST http://localhost:8000/demo/scenario \
  -H "Content-Type: application/json" \
  -d '{\"scenario\":\"add_ai_nodes_row_c\",\"action\":\"start\",\"duration_s\":180}'

# Check active scenarios
curl http://localhost:8000/demo/scenarios

# Monitor state
curl http://localhost:8000/state/overview

# Wait 2-3 minutes for optimizer cycles

# Check actions log
curl http://localhost:8000/actions/log
```

- [ ] Scenario starts successfully
- [ ] IMS deviation rises (visible in state)
- [ ] Actions appear in log
- [ ] Scenario stops automatically or manually

### 8. IMS Training (Optional)
```powershell
# Train IMS on demo data (requires sufficient samples)
curl -X POST http://localhost:8000/ims/train \
  -H "Content-Type: application/json" \
  -d '{\"n_clusters\":8}'

# List models
curl http://localhost:8000/ims/models
```

- [ ] Training succeeds (needs 100+ nominal samples)
- [ ] Model appears in models list
- [ ] Model marked as active

### 9. Run Tests
```powershell
pytest tests/ -v
```

- [ ] All IMS tests pass
- [ ] All optimizer tests pass
- [ ] All API tests pass

### 10. API Documentation
Open browser to: http://localhost:8000/docs

- [ ] Swagger UI loads
- [ ] All endpoints documented
- [ ] Try It Out feature works

## Common Issues & Solutions

### Issue: "Database connection failed"
**Solution**: Check `DATABASE_URL` in `.env`. For SQLite, ensure directory exists.

### Issue: "Import errors" when starting
**Solution**: Activate virtual environment, reinstall requirements.

### Issue: "No data available" in state overview
**Solution**: Run `demo_generator.py` to populate data, wait 1-2 minutes for rollups.

### Issue: "Rate limited" in action logs
**Solution**: Expected behavior. Default limit is 120s between writes to same device.

### Issue: Tests fail with "event loop" errors
**Solution**: Ensure `pytest-asyncio` installed, tests use `@pytest.mark.asyncio`.

### Issue: WebSocket disconnects frequently
**Solution**: Check firewall/proxy settings, ensure `uvicorn` has proper async support.

## Production Deployment Checklist

### Before Going Live
- [ ] Switch `DATABASE_URL` to Postgres/TimescaleDB
- [ ] Set `DEBUG=false` in `.env`
- [ ] Configure proper `LOG_LEVEL` (INFO or WARNING)
- [ ] Set up Redis for pub/sub (optional)
- [ ] Review and adjust all limits in `.env`
- [ ] Set `DEFAULT_MODE=advisory` initially
- [ ] Deploy behind reverse proxy (nginx/traefik)
- [ ] Configure CORS origins properly
- [ ] Set up monitoring and alerting
- [ ] Implement proper authentication/authorization
- [ ] Schedule regular IMS retraining (weekly/monthly)
- [ ] Set up automated backups

### Post-Deployment
- [ ] Monitor logs for errors
- [ ] Verify background tasks running
- [ ] Check action execution success rate
- [ ] Monitor J/prompt reduction
- [ ] Validate SLA compliance
- [ ] Review action audit trail
- [ ] Generate and review weekly reports

## Ready for Demo! 🚀

Once all checks pass:
1. Keep server running
2. Start demo generator
3. Run heat spike scenario
4. Show frontend the WebSocket events and REST APIs
5. Demonstrate action execution and energy savings

**All systems go!**
