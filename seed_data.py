from db.models import Base, engine, Device, NetworkLink, Category
from db.database import SessionLocal
from werkzeug.security import generate_password_hash

Base.metadata.create_all(engine)

session = SessionLocal()

if session.query(Device).first():
    print("Database already seeded.")
    session.close()
    exit(0)

# Categories
categories = ["radio", "ap"]
cat_map = {}
for cat_name in categories:
    existing = session.query(Category).filter_by(name=cat_name).first()
    if not existing:
        existing = Category(name=cat_name)
        session.add(existing)
        session.flush()
    cat_map[cat_name] = existing.id

# Devices
devices = [
    # Site A - Multiple IPs
    Device(ip="1.1.1.1", hostname="Router-A1", device_name="Router-A1", location="Site-A", category_id=cat_map["radio"], status=True),
    Device(ip="1.1.1.2", hostname="Switch-A1", device_name="Switch-A1", location="Site-A", category_id=cat_map["radio"], status=True),
    Device(ip="1.1.1.3", hostname="Server-A1", device_name="Server-A1", location="Site-A", category_id=cat_map["ap"], status=True),

    # Site B - Multiple IPs
    Device(ip="5.5.5.5", hostname="Router-B1", device_name="Router-B1", location="Site-B", category_id=cat_map["radio"], status=True),
    Device(ip="5.5.5.6", hostname="Switch-B1", device_name="Switch-B1", location="Site-B", category_id=cat_map["radio"], status=True),

    # Site C - Single IP
    Device(ip="3.3.3.3", hostname="Router-C1", device_name="Router-C1", location="Site-C", category_id=cat_map["radio"], status=True),

    # Site D - For mesh
    Device(ip="7.7.7.7", hostname="Router-D1", device_name="Router-D1", location="Site-D", category_id=cat_map["radio"], status=True),

    # Site E - For hub-and-spoke
    Device(ip="9.9.9.9", hostname="Hub-E1", device_name="Hub-E1", location="Site-E", category_id=cat_map["radio"], status=True),
    Device(ip="10.10.10.1", hostname="Spoke-E1", device_name="Spoke-E1", location="Site-E-Spoke1", category_id=cat_map["radio"], status=True),
    Device(ip="10.10.10.2", hostname="Spoke-E2", device_name="Spoke-E2", location="Site-E-Spoke2", category_id=cat_map["radio"], status=True),

    # Site F - For loop/ring
    Device(ip="11.11.11.1", hostname="Ring-F1", device_name="Ring-F1", location="Site-F", category_id=cat_map["radio"], status=True),
    Device(ip="11.11.11.2", hostname="Ring-F2", device_name="Ring-F2", location="Site-F", category_id=cat_map["radio"], status=True),
    Device(ip="11.11.11.3", hostname="Ring-F3", device_name="Ring-F3", location="Site-F", category_id=cat_map["radio"], status=True),
    Device(ip="11.11.11.4", hostname="Ring-F4", device_name="Ring-F4", location="Site-F", category_id=cat_map["radio"], status=True),

    # Device with some down links to test node status derivation
    Device(ip="192.168.1.1", hostname="Degraded-Node", device_name="Degraded-Node", location="Site-G", category_id=cat_map["radio"], status=True),
    Device(ip="192.168.1.2", hostname="Peer-Node1", device_name="Peer-Node1", location="Site-G", category_id=cat_map["radio"], status=True),
    Device(ip="192.168.1.3", hostname="Peer-Node2", device_name="Peer-Node2", location="Site-G", category_id=cat_map["radio"], status=True),
]

for d in devices:
    session.add(d)
session.flush()

# Links demonstrating various topologies

# One-to-One
# A → B (primary MPLS)
session.add(NetworkLink(source_ip="1.1.1.1", destination_ip="5.5.5.5", remark="Primary MPLS", link_type="mpls", bandwidth="1Gbps", status=True))

# One-to-Many
# 1.1.1.1 → 3.3.3.3 and 1.1.1.1 → 7.7.7.7
session.add(NetworkLink(source_ip="1.1.1.1", destination_ip="3.3.3.3", remark="Secondary Link", link_type="fibre", bandwidth="100Mbps", status=True))
session.add(NetworkLink(source_ip="1.1.1.1", destination_ip="7.7.7.7", remark="Backup Link", link_type="radio", bandwidth="50Mbps", status=True))

# Many-to-One
# 3.3.3.3 → 5.5.5.5, 7.7.7.7 → 5.5.5.5
session.add(NetworkLink(source_ip="3.3.3.3", destination_ip="5.5.5.5", remark="Link C→B", link_type="fibre", bandwidth="500Mbps", status=True))
session.add(NetworkLink(source_ip="7.7.7.7", destination_ip="5.5.5.5", remark="Link D→B", link_type="mpls", bandwidth="1Gbps", status=True))

# Many-to-Many
# 1.1.1.1 → 3.3.3.3 (already exists), 1.1.1.1 → 5.5.5.5 (already exists)
# 5.5.5.5 → 7.7.7.7
session.add(NetworkLink(source_ip="5.5.5.5", destination_ip="7.7.7.7", remark="Link B→D", link_type="fibre", bandwidth="200Mbps", status=True))
# 3.3.3.3 → 7.7.7.7
session.add(NetworkLink(source_ip="3.3.3.3", destination_ip="7.7.7.7", remark="Link C→D", link_type="radio", bandwidth="100Mbps", status=True))

# Loop / Ring topology (Site-F internal ring)
session.add(NetworkLink(source_ip="11.11.11.1", destination_ip="11.11.11.2", remark="Ring segment 1-2", link_type="fibre", bandwidth="10Gbps", status=True))
session.add(NetworkLink(source_ip="11.11.11.2", destination_ip="11.11.11.3", remark="Ring segment 2-3", link_type="fibre", bandwidth="10Gbps", status=True))
session.add(NetworkLink(source_ip="11.11.11.3", destination_ip="11.11.11.4", remark="Ring segment 3-4", link_type="fibre", bandwidth="10Gbps", status=True))
session.add(NetworkLink(source_ip="11.11.11.4", destination_ip="11.11.11.1", remark="Ring segment 4-1", link_type="fibre", bandwidth="10Gbps", status=True))

# Mesh topology (Site-A internal and cross-site)
session.add(NetworkLink(source_ip="1.1.1.1", destination_ip="1.1.1.2", remark="A1→Switch-A1", link_type="fibre", bandwidth="1Gbps", status=True))
session.add(NetworkLink(source_ip="1.1.1.2", destination_ip="1.1.1.3", remark="Switch-A1→Server", link_type="fibre", bandwidth="1Gbps", status=True))
session.add(NetworkLink(source_ip="1.1.1.1", destination_ip="1.1.1.3", remark="A1→Server direct", link_type="fibre", bandwidth="1Gbps", status=True))

# Multiple IPs per site links (Site-A → Site-B from different IPs)
session.add(NetworkLink(source_ip="1.1.1.2", destination_ip="5.5.5.6", remark="Switch-A1→Switch-B1", link_type="fibre", bandwidth="1Gbps", status=True))
session.add(NetworkLink(source_ip="1.1.1.3", destination_ip="5.5.5.5", remark="Server-A1→Router-B1", link_type="mpls", bandwidth="500Mbps", status=True))

# Hub-and-spoke (Site-E hub to spokes)
session.add(NetworkLink(source_ip="9.9.9.9", destination_ip="10.10.10.1", remark="Hub→Spoke1", link_type="radio", bandwidth="100Mbps", status=True))
session.add(NetworkLink(source_ip="9.9.9.9", destination_ip="10.10.10.2", remark="Hub→Spoke2", link_type="radio", bandwidth="100Mbps", status=True))

# Redundant paths: Site-G with multiple paths
session.add(NetworkLink(source_ip="192.168.1.1", destination_ip="192.168.1.2", remark="Primary path G1→G2", link_type="fibre", bandwidth="1Gbps", status=True))
session.add(NetworkLink(source_ip="192.168.1.1", destination_ip="192.168.1.3", remark="Secondary path G1→G3", link_type="fibre", bandwidth="1Gbps", status=True))
# This creates a redundant path: G1→G2 can also be reached via G1→G3→G2
session.add(NetworkLink(source_ip="192.168.1.3", destination_ip="192.168.1.2", remark="Third path G3→G2", link_type="fibre", bandwidth="1Gbps", status=True))

# Down links to test node status derivation
# One link down on 192.168.1.1 (degraded node - should show YELLOW)
session.add(NetworkLink(source_ip="192.168.1.1", destination_ip="192.168.1.2", remark="Degraded link (down)", link_type="fibre", bandwidth="1Gbps", status=False))

# Cross-site links from Site-A to other sites
session.add(NetworkLink(source_ip="1.1.1.1", destination_ip="11.11.11.1", remark="A→Ring-F1", link_type="mpls", bandwidth="1Gbps", status=True))

session.commit()

from werkzeug.security import generate_password_hash
from db.models import User
existing = session.query(User).first()
if not existing:
    admin = User(user="admin", passwd=generate_password_hash("admin"), must_change_password=False)
    session.add(admin)
    session.commit()

session.close()
print("Seed data created successfully!")
print(f"  Devices: {len(devices)}")
print(f"  Links: multiple topologies seeded")
