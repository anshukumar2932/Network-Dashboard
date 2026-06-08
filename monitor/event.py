from extensions import socketio
def send_topology_update(data):
    socketio.emit("topology_update",data)

def send_alert(alert):
    socketio.emit("alert",alert)