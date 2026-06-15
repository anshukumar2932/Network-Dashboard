# Network Dashboard — Function Reference

## app.py

| Function | Line | Used | Call Sites |
|---|---|---|---|
| `generate_captcha` | 36 | Yes | `app.py:124`, `app.py:157` |
| `handle_rate_limit` | 52 | Yes | Flask `@app.errorhandler(RateLimitExceeded)` |
| `require_api_key` | 57 | **No** | Decorator defined but never applied |
| `load_user` | 71 | Yes | Flask-Login `@login_manager.user_loader` |
| `check_must_change_password` | 80 | Yes | Flask `@app.before_request` |
| `add_no_cache` | 87 | Yes | Flask `@app.after_request` |
| `create_default_admin` | 94 | Yes | `app.py:1007` |
| `captcha_image` | 112 | Yes | Route `/captcha-image` |
| `captcha_refresh` | 122 | Yes | Route `/captcha-refresh` |
| `index` | 133 | Yes | Route `/` |
| `change_password` | 161 | Yes | Route `/change-password` |
| `dashboard` | 194 | Yes | Route `/dashboard` |
| `radio` | 259 | Yes | Route `/dashboard/radio/<id>` |
| `upload_devices_template` | 271 | Yes | Route `/devices/upload/template` |
| `upload_devices` | 293 | Yes | Route `/devices/upload` |
| `location_page` | 434 | Yes | Route `/location/<location_name>` |
| `devices` | 450 | Yes | Route `/devices` |
| `delete_device_page` | 506 | Yes | Route `/devices/delete/<ip>` |
| `device_page` | 520 | Yes | Route `/device/<ip>` |
| `links_route` | 535 | Yes | Route `/links` |
| `alerts_api` | 835 | Yes | Route `/api/alerts` |
| `devices_list_api` | 843 | Yes | Route `/api/devices-list` |
| `api_devices_stats` | 849 | Yes | Route `/api/devices-stats` |
| `devices_sidebar_api` | 855 | Yes | Route `/api/devices-sidebar` |
| `delete_device_api` | 861 | Yes | Route `/api/devices/delete/<ip>` |
| `topology_api` | 873 | Yes | Route `/api/topology` |
| `topology_locations_api` | 884 | Yes | Route `/api/topology/locations` |
| `topology_location_api` | 905 | Yes | Route `/api/topology/location/<location_name>` |
| `ping_now_api` | 942 | Yes | Route `/api/ping/now` |
| `ping_status_api` | 956 | Yes | Route `/api/ping/status` |
| `locations_api` | 965 | Yes | Route `/api/locations` |
| `get_dashboard_state_api` | 971 | Yes | Route `/api/dashboard-state` GET |
| `save_dashboard_state_api` | 978 | Yes | Route `/api/dashboard-state` POST |
| `logout` | 997 | Yes | Route `/logout` |

## db/database.py

| Function | Line | Used | Call Sites |
|---|---|---|---|
| `is_valid_ip` | 16 | Yes | `app.py:664`, `app.py:671`, `database.py:36` |
| `is_valid_ip_or_empty` | 32 | **No** | Imported in `app.py:18` but never called |
| `normalize_ip` | 39 | **No** | Never imported or called |
| `is_valid_ipv4_quick` | 56 | **No** | Never imported or called |
| `_get_or_create_category` | 63 | Yes | `database.py:163`, `database.py:197`, `database.py:237` |
| `login` | 73 | Yes | `app.py:144` |
| `device_status` | 91 | **No** | Imported in `app.py:14` but never called |
| `get_all_devices` | 120 | **No** | Imported in `app.py:11` but never called |
| `all_devices_status` | 131 | Yes | `app.py:838`, `app.py:846`, `app.py:858` |
| `add_device` | 155 | Yes | `app.py:471`, `app.py:588`, `app.py:686`, `app.py:695`, `app.py:750`, `app.py:759` |
| `update_device` | 184 | Yes | `app.py:465`, `app.py:596`, `app.py:614`, `app.py:689`, `app.py:698`, `app.py:746`, `app.py:755` |
| `delete_device` | 210 | Yes | `app.py:509`, `app.py:864` |
| `add_devices_bulk` | 226 | Yes | `app.py:393` |
| `add_link` | 257 | Yes | `app.py:400`, `app.py:620`, `app.py:762` |
| `get_details_paginated` | 292 | Yes | `app.py:492` |
| `derive_node_status` | 338 | Yes | `database.py:387` (internal) |
| `get_ip_topology` | 351 | Yes | Aliased as `get_topology` at `database.py:443` |
| `get_locations` | 446 | Yes | `app.py:887`, `app.py:968` |
| `get_location_devices` | 467 | Yes | `app.py:437`, `app.py:908` |
| `get_location_links` | 486 | Yes | `app.py:438`, `app.py:909` |
| `get_device_by_ip` | 516 | Yes | `app.py:454`, `app.py:462`, `app.py:523`, `app.py:587`, `app.py:602`, `app.py:613`, `app.py:680`, `app.py:681` |
| `get_links_for_device` | 524 | Yes | `app.py:526` |
| `get_devices_stats` | 559 | Yes | `app.py:852` |
| `get_all_links` | 582 | Yes | `app.py:230`, `app.py:804` |
| `get_links_paginated` | 610 | Yes | `app.py:218`, `app.py:792` |
| `get_link_filter_options` | 729 | Yes | `app.py:233`, `app.py:807` |
| `update_link` | 751 | Yes | `app.py:702` |
| `delete_link` | 778 | Yes | `app.py:557` |
| `get_links_by_ip` | 794 | **No** | Imported in `app.py:16` but never called |
| `cache_topology` | 821 | Yes | `app.py:880` |
| `get_cached_topology` | 838 | Yes | `app.py:876` |
| `invalidate_cache_for` | 851 | Yes | `app.py:466`, `app.py:472`, `app.py:515`, `app.py:561`, `app.py:630`, `app.py:707`, `app.py:767` |
| `category_list` | 860 | Yes | `database.py:527`, `app.py:309`, `app.py:497` |
| `category_add` | 867 | Yes | `app.py:342`, `app.py:364` |
| `get_dashboard_state` | 891 | Yes | `app.py:974`, `app.py:992` |
| `save_dashboard_state` | 909 | Yes | `app.py:982` |

## db/models.py

| Function | Line | Used | Call Sites |
|---|---|---|---|
| `set_sqlite_pragma` | 13 | Yes | SQLAlchemy `@event.listens_for(engine, "connect")` |

## monitor/monitor.py

| Function | Line | Used | Call Sites |
|---|---|---|---|
| `check_device` | 14 | Yes | `monitor.py:44` |
| `chunk` | 37 | Yes | `monitor.py:52` |
| `process_batch` | 42 | Yes | `monitor.py:53` |
| `monitor_devices` | 50 | Yes | `monitor.py:79` |
| `update_link_status` | 58 | Yes | `monitor.py:121` |
| `run` | 69 | Yes | `scheduler.py:10`, `app.py:950` |

## monitor/ping.py

| Function | Line | Used | Call Sites |
|---|---|---|---|
| `ping_device` | 5 | Yes | `monitor.py:18` |
| `_ping` | 10 | Yes | `ping.py:26` (inner) |

## monitor/alert.py

| Function | Line | Used | Call Sites |
|---|---|---|---|
| `send_email` | 20 | Yes | `alert.py:77`, `alert.py:111` |
| `send_alert_down` | 49 | Yes | `monitor.py:146` |
| `send_alert_up` | 83 | Yes | `monitor.py:150` |

## monitor/event.py

| Function | Line | Used | Call Sites |
|---|---|---|---|
| `send_topology_update` | 2 | **No** | Never imported or called |
| `send_alert` | 5 | **No** | Never imported or called |

---

## Unused Functions Summary

| Function | File | Line | Notes |
|---|---|---|---|
| `require_api_key` | app.py | 57 | Decorator defined, never applied to any route |
| `is_valid_ip_or_empty` | db/database.py | 32 | Imported in app.py but never called |
| `normalize_ip` | db/database.py | 39 | Never imported or called |
| `is_valid_ipv4_quick` | db/database.py | 56 | Never imported or called |
| `device_status` | db/database.py | 91 | Imported in app.py but never called |
| `get_all_devices` | db/database.py | 120 | Imported in app.py but never called |
| `get_links_by_ip` | db/database.py | 794 | Imported in app.py but never called |
| `send_topology_update` | monitor/event.py | 2 | Never imported or called |
| `send_alert` | monitor/event.py | 5 | Never imported or called |
