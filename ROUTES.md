# Network Dashboard — Routes

## Pages

| Route | Methods | Auth | Description |
|---|---|---|---|
| `/` | GET, POST | No | Login page with captcha |
| `/change-password` | GET, POST | Yes | Change password (forced for new users) |
| `/dashboard` | GET | Yes | Main dashboard — paginated link table with filters, sorting, search |
| `/dashboard/radio/<id>` | GET, POST | Yes | Radio detail / redirect to device by IP |
| `/devices` | GET, POST | Yes | Device list — add/edit/search/sort devices |
| `/device/<ip>` | GET | Yes | Single device detail with its links |
| `/devices/upload` | GET, POST | Yes | Bulk import devices & links from Excel |
| `/devices/upload/template` | GET | Yes | Download Excel upload template |
| `/devices/delete/<ip>` | GET | Yes | Delete device by IP (redirects to `/devices`) |
| `/links` | GET, POST | Yes | Link management — add/edit/delete links with new-device location flow |
| `/location/<location_name>` | GET | Yes | Location page — devices & links for a location |
| `/logout` | GET | Yes | Log out and redirect to login |

## JSON API

| Route | Methods | Auth | Description |
|---|---|---|---|
| `/api/alerts` | GET | Yes | List all down devices |
| `/api/devices-list` | GET | Yes | Full device list with status |
| `/api/devices-stats` | GET | Yes | Device status statistics |
| `/api/devices-sidebar` | GET | Yes | Device sidebar data |
| `/api/devices/delete/<ip>` | DELETE | Yes | Delete device (JSON response) |
| `/api/topology` | GET | Yes | Full topology graph (cached 30s) |
| `/api/topology/locations` | GET | Yes | Topology location nodes |
| `/api/topology/location/<location_name>` | GET | Yes | Topology nodes & edges for one location |
| `/api/ping/now` | GET | Yes | Trigger background ping sweep |
| `/api/ping/status` | GET | Yes | Check if ping sweep is running |
| `/api/locations` | GET | Yes | List all locations with status |
| `/api/dashboard-state` | GET | Yes | Get saved dashboard state (zoom, pan, etc.) |
| `/api/dashboard-state` | POST | Yes | Save dashboard state |

## Utility

| Route | Methods | Auth | Description |
|---|---|---|---|
| `/captcha-image` | GET | No | Serve current captcha image |
| `/captcha-refresh` | GET | No | Regenerate and serve new captcha image |
