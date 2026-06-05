# Project Charter

## Wireless Network Topology & Monitoring Dashboard


### Project Objective

Develop an enterprise-grade Wireless Network Topology & Monitoring Dashboard for Cambium PTP670, Force180, and Force300 links connecting mines, offices, and remote locations.

The system must provide:

* Real-time device monitoring
* Interactive topology visualization
* Device inventory management
* Email alerting
* Historical availability reporting
* Zero licensing cost
* Scalability from 42 devices to 500+ devices

---

# Infrastructure

## Server

Current Hardware

```text
OS: Windows 11 Pro
CPU: Intel i5 9th Gen
RAM: 8 GB
Storage: 1 TB HDD
```

Reason:

* Faster SQLite performance
* Faster dashboard loading
* Faster reporting

---

# Approved Technology Stack

| Component             | Technology                                 |
| --------------------- | ------------------------------------------ |
| Database              | SQLite                                     |
| Backend Framework     | Flask                                      |
| Frontend              | HTML5 + JavaScript                         |
| UI Framework          | Bootstrap 5                                |
| Network Graph         | Cytoscape.js                               |
| Charts                | Chart.js                                   |
| Maps (Future)         | Leaflet                                    |
| Scheduler             | APScheduler                                |
| Monitoring Engine     | Python Async Ping Engine (asyncio + ping3) |
| Email Alerts          | SMTP                                       |
| Authentication        | Flask-Login / Session Authentication       |
| Web Server            | Waitress (Windows Production Server)       |
| Deployment            | Windows Service (NSSM)                     |
| Packaging (Future)    | PyInstaller                                |
| Configuration Storage | JSON + SQLite                              |
| Logging               | Python Logging                             |
| Data Import           | Excel / CSV Upload                         |
| Real-Time Updates     | AJAX Polling (30 sec refresh)              |
| Backup                | SQLite File Backup                         |


---

# Phase 1 – Data Modeling

Duration: 1 Week

## Objective

Convert Excel inventory into structured data.

### Deliverables

#### Sites

Examples:

```text
Lohardaga Office
Bagru Mines
Pakhar Mines
Samri Mines
Shrendag Mines
```

#### Devices

Examples:

```text
PTP670
Force180
Force300
```

#### Links

Examples:

```text
Lohardaga ↔ Bagru
Bagru ↔ Shrendag
Samri ↔ Kujam
```

### Database Design

#### Sites

```sql
CREATE TABLE sites(
 id INTEGER PRIMARY KEY,
 location TEXT,
 type TEXT
);
```

#### Devices

```sql
CREATE TABLE devices(
    id INTEGER PRIMARY KEY,
    site_id INTEGER NOT NULL,
    hostname TEXT,
    model TEXT,
    ip_address TEXT UNIQUE,
    status TEXT,
    last_seen DATETIME,

    FOREIGN KEY (site_id)
        REFERENCES sites(id)
);
```

#### Links

```sql
CREATE TABLE links(
    id INTEGER PRIMARY KEY,

    source_site INTEGER NOT NULL,
    destination_site INTEGER NOT NULL,

    device_a INTEGER,
    device_b INTEGER,

    FOREIGN KEY (source_site)
        REFERENCES sites(id),

    FOREIGN KEY (destination_site)
        REFERENCES sites(id),

    FOREIGN KEY (device_a)
        REFERENCES devices(id),

    FOREIGN KEY (device_b)
        REFERENCES devices(id)
);
```

---

# Phase 2 – Monitoring Engine

Duration: 1 Week

## Objective

Monitor all devices automatically.

### Monitoring Rules

Polling Interval:

```text
Every 5 Minutes
```

Retry Policy:

```text
Ping Attempt 1
Ping Attempt 2
Ping Attempt 3
```

Device Status:

```text
Any Ping Success = UP

All 3 Failures = DOWN
```

---

## Monitoring Architecture

```text
Scheduler
    ↓
Load Devices
    ↓
Create Batches
    ↓
Async Ping
    ↓
Update Database
    ↓
Generate Alert List
    ↓
Send Email
```

---

## Batch Configuration

Current Scale

```text
42 Devices
```

Future Scale

```text
500 Devices
```

Configuration

```yaml
batch_size: 50
timeout: 1 second
retries: 3
poll_interval: 5 minutes
```

---

# Phase 3 – Database Retention Policy

Duration: 2 Days

## Objective

Prevent database growth.

### Raw Ping Storage

Retention:

```text
1 Hour Only
```

Table

```sql
CREATE TABLE ping_history(
 id INTEGER PRIMARY KEY,
 device_id INTEGER,
 ping_time DATETIME,
 latency_ms REAL,
 status TEXT
);
```

Cleanup Job

```sql
DELETE FROM ping_history
WHERE ping_time < datetime('now','-1 hour');
```

---

### Current Device Status

Table

```sql
CREATE TABLE device_status(
 device_id INTEGER PRIMARY KEY,
 status TEXT,
 latency REAL,
 fail_count INTEGER,
 last_seen DATETIME
);
```

Retention

```text
Permanent
```

---

### Hourly Statistics

Table

```sql
CREATE TABLE hourly_stats(
 device_id INTEGER,
 stat_hour DATETIME,
 success_rate REAL,
 avg_latency REAL,
 downtime_seconds INTEGER
);
```

Retention

```text
90 Days
```

---

# Phase 4 – Email Alert System

Duration: 3 Days

## Objective

Notify network team of outages.

### Alert Logic

Process:

```text
Check All Devices
        ↓
Create Down Device List
        ↓
Send Single Email
```

Do NOT send one email per device.

---

### Example

Subject:

```text
Network Alert – Devices Down
```

Content:

```text
Devices Down:

1. Lohardaga → Bagru
2. Samri → Kujam
3. Pakhar → Antipani

Monitoring Time:
10:00 AM

Retry Attempts:
3
```

---

## Anti-Spam Policy

### First Failure

```text
Send Alert
```

### Device Still Down

```text
No Additional Email
```

### Recovery

```text
Send Recovery Email
```

Example:

```text
Subject: Device Recovery

Samri → Kujam

Status:
Recovered

Downtime:
18 Minutes
```

---

# Phase 5 – Backend API

Duration: 1 Week

## Objective

Provide data to dashboard.

### APIs

```http
GET /api/sites
GET /api/devices
GET /api/links
GET /api/topology
GET /api/alerts
GET /api/stats
```

---

### WebSocket

```http
/ws/topology
```

Events

```text
Device Up
Device Down
Recovery
Status Change
```

---

# Phase 6 – Dashboard Development

Duration: 2 Weeks

## Objective

Build NOC Dashboard.

### Navigation

```text
Dashboard
Topology
Sites
Devices
Alerts
Reports
Settings
```

---

## Dashboard Layout

```text
┌────────────────────────────┐
│ KPI Cards                  │
├────────────────────────────┤
│                            │
│     Network Topology       │
│                            │
├───────────┬────────────────┤
│ Alerts    │ Device Details │
└───────────┴────────────────┘
```

---

### KPI Cards

```text
Total Devices
Devices Up
Devices Down
Availability %
Active Alerts
```

---

# Phase 7 – Topology Visualization

Duration: 1 Week

## Technology

```text
Cytoscape.js
```

### Node

Represents:

```text
Mine
Office
WB
Remote Site
```

### Edge

Represents:

```text
Wireless Link
```

### Colors

```text
Green = Healthy

Yellow = Warning

Red = Down
```

---

# Phase 8 – Reporting

Duration: 1 Week

## Reports

### Daily

```text
Availability
Downtime
Device Status
```

### Monthly

```text
Site Availability
Top Outages
Worst Performing Links
```

Export Formats

```text
PDF
Excel
```

---

# Phase 9 – Site, Location & Device Management

Duration: 1 Week

## Objective

Provide a centralized interface for managing network inventory without requiring database access.

The system shall allow administrators to add, update, and manage:

* New Locations
* New Sites
* New Devices
* New Wireless Links

All entries shall be added using text-based input fields. Dropdowns will be avoided to support faster data entry and future scalability.

# Phase 10 – Application Packaging & One-Click Installation (Future)


## Objective

Package the complete monitoring system into a deployable executable that can be installed on a Windows machine without requiring manual Python, Node.js, or dependency installation.

The installation process should be executable by IT personnel with minimal technical knowledge.

---

# Deployment Goal

Target Environment:

```text
Windows 11 Pro
Intel i5 9th Gen
8 GB RAM
500 Devices
```

Installation Method:

```text
Double Click Installer
      ↓
Install Application
      ↓
Configure Settings
      ↓
Start Monitoring
```

No manual command-line operations should be required.

---

# Packaging Strategy

## Components to Package

### Backend

```text
FastAPI
Ping Engine
APScheduler
Email Alert Engine
SQLite Database
```

### Frontend

```text
React Dashboard
Topology View
Reports
Configuration Pages
```

### Database

```text
SQLite
```

Database file will be created automatically during installation.

---

# Build Process

## Step 1 – Build Frontend

Generate static frontend files.

```bash
npm run build
```

Output:

```text
dist/
```

---

## Step 2 – Bundle Backend

Tool:

```text
PyInstaller
```

Install:

```bash
pip install pyinstaller
```

Build:

```bash
pyinstaller --onefile main.py
```

Output:

```text
monitoring.exe
```

---

## Step 3 – Create Application Structure

```text
NetworkMonitoring/
│
├── monitoring.exe
├── network.db
├── config/
│   └── settings.json
│
├── logs/
│
├── frontend/
│   └── dist/
│
└── backups/
```

---

# Configuration Wizard

During first launch:

## General Settings

```text
Company Name
Site Name
Administrator Email
```

---

## Monitoring Settings

```text
Polling Interval
Ping Timeout
Retry Count
Batch Size
```

Default:

```text
5 Minutes
1 Second Timeout
3 Retries
50 Devices Per Batch
```

---

## Email Settings

```text
SMTP Server
SMTP Port
Username
Password
Sender Email
Recipient Email
```

Test Button:

```text
Send Test Email
```

---

# Windows Service Installation

## Objective

Monitoring should continue running even after user logout.

Tool:

```text
NSSM
(Non-Sucking Service Manager)
```

Install service:

```bash
nssm install NetworkMonitoring
```

Result:

```text
Windows Service
Automatic Startup
Background Monitoring
```

---

# Dashboard Access

After installation:

```text
http://localhost:8000
```

or

```text
http://SERVER-IP:8000
```

Accessible from:

```text
Desktop
Laptop
Mobile Browser
```

within the network.

---

# Backup Strategy

Automatic Backup:

```text
Daily
```

Backup Content:

```text
SQLite Database
Configuration Files
```

Location:

```text
backups/
```

Retention:

```text
30 Days
```

---

# Application Update Process

Future versions shall support:

```text
Export Configuration
Install New Version
Import Configuration
Resume Monitoring
```

No database loss during upgrades.

---

# Installer Creation

Recommended Tool:

```text
Inno Setup
```

Output:

```text
NetworkMonitoringSetup.exe
```

Installation Flow:

```text
Welcome
↓
License
↓
Install Location
↓
Create Database
↓
Create Windows Service
↓
Launch Dashboard
```

---

# Final Deliverables

```text
NetworkMonitoringSetup.exe
```

Includes:

```text
FastAPI Backend
React Frontend
SQLite Database
Ping Engine
Email Alerts
Topology Engine
Reports
Windows Service
Auto Backup
```

---

# Success Criteria

Administrator shall be able to:

```text
1. Copy Setup File
2. Run Installer
3. Configure Email
4. Import Device Inventory
5. Start Monitoring
```

without installing:

```text
Python
Node.js
SQLite
NPM
Git
```

manually.

The complete application shall be operational within 15 minutes of installation.

---

## Dashboard

### Inventory Management

```text
Add New Location
Add New Site
Add New Device
Add New Link
```

---

## Location Management

### Purpose

A Location represents a geographical area, district, or operational region.

Examples:

```text
Lohardaga
Latehar
Palamu
Ranchi
```

### Input Fields

```text
Location Name
Description
Latitude (Optional)
Longitude (Optional)
```

### Validation

* Location name must be unique.
* Duplicate locations are not permitted.

---

## Site Management

### Purpose

A Site represents a physical office, mine, workshop, repeater station, or remote facility.

Examples:

```text
Bagru Mines
Pakhar Mines
Lohardaga Office
Samri Mines
```

### Input Fields

```text
Site Name
Site Type
Location Name
Latitude
Longitude
Remarks
```

### Site Types

```text
Office
Mine
Workshop
Remote Site
Repeater Station
Warehouse
```

### Validation

* Site name must be unique.
* Location must already exist.
* Coordinates are optional.

---

## Device Management

### Purpose

Register network devices for monitoring and topology generation.

Examples:

```text
PTP670
Force180
Force300
Switch
Router
```

### Input Fields

```text
Hostname
Management IP Address
Device Model
Device Type
Site Name
Serial Number
Firmware Version
```

### Validation

* IP Address must be unique.
* Hostname must be unique.
* Device must belong to an existing site.

---

## Link Management

### Purpose

Create logical and physical relationships between devices and sites.

Examples:

```text
Lohardaga ↔ Bagru
Bagru ↔ Shrendag
Samri ↔ Kujam
```

### Input Fields

```text
Source Site
Destination Site
Source Device IP
Destination Device IP
Link Type
Bandwidth
```

### Validation

* Source and destination devices must exist.
* Duplicate links are not permitted.

---

## Topology Auto Generation

Upon creation of a new link:

```text
New Link Added
        ↓
Database Updated
        ↓
Topology Regenerated
        ↓
Dashboard Updated
```

No manual topology drawing is required.

---

## Search & Discovery

The dashboard shall support text-based search for:

```text
Location Name
Site Name
Device Name
IP Address
Link Name
```

Examples:

```text
Search: Bagru

Result:
Bagru Mines
Connected Devices
Connected Links
Current Status
```

---

## Audit Requirements

All inventory changes shall be logged.

Track:

```text
Created By
Modified By
Date Created
Date Modified
```

This ensures accountability and change tracking for all additions and modifications.

---

## Success Criteria

Administrators shall be able to:

```text
Add New Location
Add New Site
Add New Device
Add New Link
```

without database access and without modifying application code.

All newly added inventory shall automatically appear in:

```text
Topology View
Monitoring Engine
Alert System
Reports
Search Results
```


---

# Success Criteria

### Performance

```text
500 Devices Supported
```

### Monitoring

```text
5-Minute Polling
3 Retry Verification
```

### Alerting

```text
Single Consolidated Email
Recovery Notification
```

### Storage

```text
Raw Ping History = 1 Hour
```

### Availability

```text
Dashboard Load < 3 Seconds
```

### Cost

```text
Software Licensing Cost = ₹0
```

---

# Final Architecture

Cambium Devices
↓
Async Ping Engine
↓
SQLite
↓
FastAPI
↓
React Dashboard
↓
Cytoscape.js Topology

Additional Services

APScheduler → Monitoring

SMTP → Email Alerts

WebSocket → Real-Time Updates

ECharts → Reports

Leaflet → Future GIS View
