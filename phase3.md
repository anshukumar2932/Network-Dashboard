For your architecture, WebSocket is the right choice because you want:

```text
Ping Engine
    ↓
SQLite Updated
    ↓
All Open Dashboards Updated Immediately
```

### 1. Install

```bash
pip install flask-socketio eventlet
```

---

### 2. app.py

Replace:

```python
app.run(
    host="0.0.0.0",
    port=5000,
    debug=True
)
```

with:

```python
from flask_socketio import SocketIO

app = Flask(__name__)
app.secret_key = "secret"

socketio = SocketIO(
    app,
    cors_allowed_origins="*"
)
```

At the bottom:

```python
if __name__ == "__main__":

    scheduler.start()

    Base.metadata.create_all(engine)

    print("Database tables created.")

    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=True
    )
```

---

### 3. Create a Central Event Function

Create `monitor/events.py`

```python
from app import socketio

def send_topology_update(data):

    socketio.emit(
        "topology_update",
        data
    )

def send_alert(alert):

    socketio.emit(
        "alert",
        alert
    )
```

---

### 4. Emit After Monitoring

Example scheduler:

```python
def check_devices():

    devices = get_all_devices()

    for device in devices:

        result = ping(device.ip)

        update_device_status(
            device.id,
            result
        )

    topology = topology_data()

    socketio.emit(
        "topology_update",
        topology
    )
```

Now every dashboard receives updates immediately.

---

### 5. Frontend

In dashboard page:

```html
<script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
```

Connect:

```javascript
const socket = io();
```

---

### 6. Receive Topology Updates

```javascript
socket.on(
    "topology_update",
    function(data){

        console.log(
            "Topology Updated",
            data
        );

        updateGraph(data);

    }
);
```

---

### 7. Alerts

Backend:

```python
socketio.emit(
    "alert",
    {
        "device":"PTP670-Bagru",
        "status":"DOWN"
    }
)
```

Frontend:

```javascript
socket.on(
    "alert",
    function(data){

        showAlert(
            data.device +
            " is " +
            data.status
        );

    }
);
```

---

### 8. Connection Status

Frontend:

```javascript
socket.on(
    "connect",
    ()=>{
        console.log(
            "Connected"
        );
    }
);

socket.on(
    "disconnect",
    ()=>{
        console.log(
            "Disconnected"
        );
    }
);
```

---

### 9. For Cytoscape

Your dashboard flow becomes:

```text
Dashboard Loads
        ↓
GET /api/topology
        ↓
Create Cytoscape Graph
        ↓
WebSocket Connected
        ↓
Device Goes Down
        ↓
Ping Engine Detects
        ↓
Database Updated
        ↓
socketio.emit()
        ↓
Graph Node Changes Color
```

Example:

```javascript
function updateGraph(data){

    data.devices.forEach(device=>{

        const node =
        cy.getElementById(
            device.id
        );

        node.data(
            "status",
            device.status
        );

        node.style(
            "background-color",
            device.status
            ? "#28a745"
            : "#dc3545"
        );

    });

}
```

---

### One Important Design Improvement

Avoid importing `socketio` inside monitoring modules because it often creates circular imports.

Create a dedicated file:

```python
# extensions.py

from flask_socketio import SocketIO

socketio = SocketIO(
    cors_allowed_origins="*"
)
```

Then:

```python
# app.py

from extensions import socketio

socketio.init_app(app)
```

And anywhere:

```python
from extensions import socketio

socketio.emit(
    "topology_update",
    topology_data()
)
```

This scales much better when your monitoring system grows from 42 devices to 500+ devices.
