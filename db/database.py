from sqlalchemy.orm import sessionmaker
from db.models import engine,User,Link,Device
from werkzeug.security import generate_password_hash, check_password_hash    

SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False
)

def login(username,password):
    session=SessionLocal()
    try:
        user=session.query(User).filter_by(user=username).first()
        if user and check_password_hash(user.passwd,password):
            return True
        else:
            False
    except Exception as e:
        return e
    finally:
        session.close()
        
#returns list of all device(device name) with their location ,site , status
def device_status(category):
    session=SessionLocal()
    try:
        radios=session.query(Device).filter(Device.category==category).all()
        if not radio:
            return None
        
        result=[]
        for radio in radios:
            ...

def topology_data():
    session = SessionLocal()

    try:
        nodes=[]
        edges=[]
        devices=session.query(Device).all()
        for device in devices:
            nodes.append({
                                "data": {
                    "id": str(device.id),
                    "label": device.hostname,
                    "ip": device.ip,
                    "status": device.status,
                    "category": device.category,
                    "site": device.site.name,
                    "location": device.site.location.name
                }
            })
        
        links = session.query(Link).all()
        for link in links:
            if not link.device_a or not link.device_b:
                continue
            edges.append({
                "data": {
                    "id": str(link.id),
                    "source": str(link.device_a),
                    "target": str(link.device_b),
                    "status": link.status
                }
            })
        return {"nodes":nodes,"edges":edges}
    finally:
        session.close()