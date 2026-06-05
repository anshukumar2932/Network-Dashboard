# Monitoring Engine Workflow

## Objective

Every 5 minutes:

1. Read all active devices from database
2. Split devices into batches
3. Ping devices asynchronously
4. Retry failed devices up to 3 times
5. Update device status
6. Store monitoring results
7. Generate down-device list
8. Send a consolidated email alert
9. Update dashboard

---

# Step 1 – Scheduler

Tool:

```python
APScheduler
```

Frequency:

```text
Every 5 Minutes
```

Workflow:

```text
Scheduler Trigger
       ↓
run_monitoring_cycle()
```

---

# Step 2 – Load Devices

Query all monitored devices.

Example:

```sql
SELECT
    id,
    hostname,
    ip_address
FROM devices
WHERE monitoring_enabled = 1;
```

Example Result:

```text
Device 1 : 10.36.24.235
Device 2 : 10.36.24.236
Device 3 : 10.36.24.237
...
```

---

# Step 3 – Create Batches

Purpose:

Avoid sending hundreds of pings simultaneously.

Configuration:

```python
BATCH_SIZE = 50
```

Example:

```text
500 Devices

Batch 1 : Device 1-50
Batch 2 : Device 51-100
Batch 3 : Device 101-150
...
```

---

# Step 4 – Async Ping

For each batch:

```text
Batch Start
      ↓
Launch Concurrent Pings
      ↓
Wait For Results
```

Example:

```python
await ping("10.36.24.235")
await ping("10.36.24.236")
await ping("10.36.24.237")
```

All run concurrently.

---

# Step 5 – Retry Failed Devices

Rule:

```text
Success on any attempt = UP

All 3 attempts fail = DOWN
```

Example:

```text
Attempt 1

Device A = Success
Device B = Failed
Device C = Failed
```

Retry:

```text
Attempt 2

Device B = Success
Device C = Failed
```

Retry:

```text
Attempt 3

Device C = Failed
```

Final:

```text
Device A = UP
Device B = UP
Device C = DOWN
```

---

# Step 6 – Update Database

Update device status table.

Example:

```sql
UPDATE device_status
SET
    status='UP',
    latency=12,
    fail_count=0,
    last_seen=CURRENT_TIMESTAMP
WHERE device_id=1;
```

For failed devices:

```sql
UPDATE device_status
SET
    status='DOWN',
    fail_count=3
WHERE device_id=1;
```

---

# Step 7 – Store Ping History

Keep only 1 hour of raw data.

Insert:

```sql
INSERT INTO ping_history(
    device_id,
    ping_time,
    latency_ms,
    status
)
VALUES(
    1,
    CURRENT_TIMESTAMP,
    12,
    'UP'
);
```

Cleanup:

```sql
DELETE FROM ping_history
WHERE ping_time <
datetime('now','-1 hour');
```

---

# Step 8 – Generate Alert List

Find newly down devices.

Rule:

```text
Previous Status = UP
Current Status = DOWN
```

Example:

```text
Bagru Router
Samri Office Switch
Kujam PTP670
```

Create:

```python
down_devices = []
```

---

# Step 9 – Send Consolidated Email

Send one email per cycle.

Never:

```text
1 Email Per Device
```

Always:

```text
1 Email Per Monitoring Cycle
```

Example:

Subject:

```text
Network Alert - 3 Devices Down
```

Body:

```text
Monitoring Time:
10:00 AM

Devices Down:

1. Bagru PTP670
   10.36.24.235

2. Samri Office Switch
   10.36.24.197

3. Kujam Router
   10.36.24.112

Retry Attempts:
3
```

---

# Step 10 – Recovery Detection

Rule:

```text
Previous Status = DOWN
Current Status = UP
```

Example:

```text
Device Recovered

Bagru PTP670

Downtime:
18 Minutes
```

Send separate recovery email.

---

# Step 11 – Dashboard Update

Dashboard reads:

```sql
device_status
```

instead of ping_history.

This keeps UI fast.

Display:

```text
Total Devices
Devices UP
Devices DOWN
Availability %
```

---

# Final Flow

Scheduler
↓
Load Devices
↓
Create Batches (50)
↓
Async Ping
↓
Retry Failed Devices (3 Times)
↓
Update Device Status
↓
Store Ping History
↓
Delete Ping History > 1 Hour
↓
Generate Alert List
↓
Send Alert Email
↓
Send Recovery Email
↓
Dashboard Refresh
