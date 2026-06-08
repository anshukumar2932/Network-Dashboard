#!/usr/bin/env python3
"""Seed test data: 3 locations, 8 sites, 40 devices, 8 links."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from db.database import SessionLocal
from db.models import Base, engine, Location, Site, Device, TopologyNode, Link

def seed():
    Base.metadata.create_all(engine)
    s = SessionLocal()

    if s.query(Device).first():
        print("Database already has devices. Run with --delete first to re-seed.")
        s.close()
        return

    locs = {}
    for name in ["Lohardaga", "Latehar", "Ranchi"]:
        loc = s.query(Location).filter(Location.name == name).first()
        if not loc:
            loc = Location(name=name)
            s.add(loc)
            s.flush()
        locs[name] = loc

    site_defs = [
        ("A1", "Lohardaga"), ("A2", "Lohardaga"),
        ("B1", "Latehar"),   ("B2", "Latehar"),
        ("C1", "Ranchi"),    ("C2", "Ranchi"),
        ("C3", "Ranchi"),    ("C4", "Ranchi"),
    ]
    sites = {}
    for name, loc_name in site_defs:
        site = s.query(Site).filter(Site.name == name).first()
        if not site:
            site = Site(name=name, location_id=locs[loc_name].id)
            s.add(site)
            s.flush()
        sites[name] = site

    print(f"Created {len(locs)} locations, {len(sites)} sites")

    # --- Devices: 5 per site (2 radios + 3 APs) = 40 total ---
    radio_count = 0
    ap_count = 0
    REACHABLE_IPS = ["8.8.8.8", "1.1.1.1", "8.8.4.4", "208.67.222.222", "208.67.220.220",
                      "8.8.8.9", "1.1.1.2", "8.8.4.5", "208.67.222.223", "208.67.220.221",
                      "8.8.8.10", "1.1.1.3", "8.8.4.6", "208.67.222.224", "208.67.220.222",
                      "8.8.8.11"]

    # Track device IDs for link creation
    site_radios = {}
    reachable_idx = 0

    for sname, site in sites.items():
        radios = []
        for r in range(1, 3):
            hostname = f"Radio-{sname}-{r}"
            ip = REACHABLE_IPS[reachable_idx % len(REACHABLE_IPS)]
            dev = Device(hostname=hostname, ip=ip, model="PTP670", category="radio", site_id=site.id)
            s.add(dev)
            s.flush()
            radios.append(dev)
            radio_count += 1
            reachable_idx += 1
        site_radios[sname] = radios

        for a in range(1, 4):
            hostname = f"AP-{sname}-{a:02d}"
            ip = f"10.{site.id}.{a}.{a+50}"
            dev = Device(hostname=hostname, ip=ip, model="Force300", category="ap", site_id=site.id)
            s.add(dev)
            s.flush()
            ap_count += 1

    print(f"Created {radio_count} radios, {ap_count} APs (total {radio_count+ap_count} devices)")

    # --- Mark some devices down ---
    # Site C4 (Ranchi): all 5 down → RED
    c4_devices = s.query(Device).filter(Device.site_id == sites["C4"].id).all()
    for d in c4_devices:
        d.status = False
    print(f"Marked {len(c4_devices)} devices in C4 as DOWN (RED site)")

    # Site B2: 2 radios down → YELLOW
    b2_radios = s.query(Device).filter(Device.site_id == sites["B2"].id, Device.category == "radio").all()
    for d in b2_radios:
        d.status = False
    print(f"Marked {len(b2_radios)} radios in B2 as DOWN (YELLOW site)")

    # Site C3: 1 AP down → YELLOW
    c3_ap = s.query(Device).filter(Device.site_id == sites["C3"].id, Device.category == "ap").first()
    if c3_ap:
        c3_ap.status = False
        print("Marked 1 AP in C3 as DOWN (YELLOW site)")

    s.commit()

    # --- Links: 8 total ---
    radio = site_radios
    links_data = [
        # a    b     device_a         device_b         status
        ("A1", "B1", radio["A1"][0], radio["B1"][0], True),   # Lohardaga ↔ Latehar
        ("A2", "B2", radio["A2"][0], radio["B2"][0], True),   # Lohardaga ↔ Latehar
        ("A1", "C1", radio["A1"][1], radio["C1"][0], True),   # Lohardaga ↔ Ranchi
        ("A2", "C2", radio["A2"][1], radio["C2"][0], True),   # Lohardaga ↔ Ranchi
        ("B1", "C1", radio["B1"][1], radio["C1"][1], True),   # Latehar ↔ Ranchi
        ("B2", "C2", radio["B2"][1], radio["C2"][1], True),   # Latehar ↔ Ranchi
        ("A1", "C3", radio["A1"][0], radio["C3"][0], True),   # Lohardaga ↔ Ranchi
        ("B1", "C4", radio["B1"][0], radio["C4"][0], False),  # Latehar ↔ Ranchi (DOWN)
    ]
    link_count = 0
    for src, dst, da, db, status in links_data:
        link = Link(
            source_site=sites[src].id, destination_site=sites[dst].id,
            device_a=da.id, device_b=db.id, status=status
        )
        s.add(link)
        link_count += 1

    s.commit()
    print(f"Created {link_count} inter-site links")
    print("Aggregation: Lohardaga↔Latehar=2, Lohardaga↔Ranchi=3, Latehar↔Ranchi=3")
    s.close()
    print("Done.")

def delete_all():
    Base.metadata.create_all(engine)
    s = SessionLocal()
    try:
        s.query(TopologyNode).delete()
        s.query(Link).delete()
        s.query(Device).delete()
        s.query(Site).delete()
        s.query(Location).delete()
        s.commit()
        print("Deleted all seed data")
    except Exception as e:
        s.rollback()
        print(f"Error: {e}")
    finally:
        s.close()

if __name__ == "__main__":
    if "--delete" in sys.argv:
        delete_all()
    else:
        seed()
