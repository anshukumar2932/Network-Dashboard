from sqlalchemy.orm import sessionmaker, selectinload
from db.models import engine,User,Link,Device,Site,Location,TopologyNode
from werkzeug.security import generate_password_hash, check_password_hash    
from sqlalchemy import select,func
from datetime import timezone
import time as _time

SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False
)

def login(username,password):
    print(f"[DB] login(username={username})")
    session=SessionLocal()
    try:
        user=session.query(User).filter_by(user=username).first()
        if user and check_password_hash(user.passwd,password):
            print(f"[DB] login() -> success for {username}")
            return user
        else:
            print(f"[DB] login() -> failed for {username}")
            return False
    except Exception as e:
        print(f"[DB] login() -> error: {e}")
        return e
    finally:
        session.close()
        
#returns list of all device(device name) with their location ,site , status
def device_status(category):
    print(f"[DB] device_status(category={category})")
    session=SessionLocal()
    try:
        devices=session.query(Device).filter(Device.category==category).options(
            selectinload(Device.site).selectinload(Site.location)
        ).all()
        if not devices:
            print(f"[DB] device_status({category}) -> None")
            return None
        
        result=[]
        for device in devices:
            result.append({
                "id":str(device.id),
                "label": device.hostname,
                "ip": device.ip,
                "status": device.status,
                "category": device.category,
                "site": device.site.name,
                "location": device.site.location.name
            })
        print(f"[DB] device_status({category}) -> {len(result)} devices")
        return result
    finally:
        session.close()

def radio_down():
    session=SessionLocal()
    try:
        device=session.query(Device).filter(Device.status==False,Device.category=="radio").first()
        return device
    finally:
        session.close()

def location_data(id):
    session=SessionLocal()
    try:
        sites=session.query(Site).options(
            selectinload(Site.location)
        ).filter(Site.location_id==id).all()
        return [{"id": s.id, "name": s.name, "location": {"id": s.location.id, "name": s.location.name} if s.location else None} for s in sites]
    finally:
        session.close()

def site_data(id):
    session=SessionLocal()
    try:
        sites=session.query(Site).options(
            selectinload(Site.location)
        ).filter(Site.id==id).all()
        return [{"id": s.id, "name": s.name, "location": {"id": s.location.id, "name": s.location.name} if s.location else None} for s in sites]
    finally:
        session.close()

def full_topology():
    t0 = _time.perf_counter()
    print("[DB] full_topology()")
    session = SessionLocal()
    try:
        sites = session.query(Site).options(
            selectinload(Site.location),
            selectinload(Site.devices)
        ).all()
        positions = get_topology_positions()

        # Device counts per site
        site_device_counts = {}
        site_down_counts = {}
        for site in sites:
            total = 0
            down = 0
            for d in site.devices:
                total += 1
                if not d.status:
                    down += 1
            site_device_counts[site.id] = total
            site_down_counts[site.id] = down

        # Site status
        def site_status(total, down):
            if total == 0: return "GREEN"
            if down == total: return "RED"
            if down > 0: return "YELLOW"
            return "GREEN"

        nodes = []
        needs_layout = False
        for site in sites:
            total = site_device_counts.get(site.id, 0)
            down = site_down_counts.get(site.id, 0)
            pos = positions.get(site.id)
            node = {
                "data": {
                    "id": f"site-{site.id}",
                    "label": site.name,
                    "status": site_status(total, down),
                    "status_bool": down == 0,
                    "location": site.location.name if site.location else "",
                    "location_id": site.location_id,
                    "device_count": total,
                    "down_count": down,
                    "type": "site"
                }
            }
            if pos:
                node["position"] = {"x": pos["x"], "y": pos["y"]}
            else:
                needs_layout = True
            nodes.append(node)

        links = session.query(Link).options(
            selectinload(Link.source),
            selectinload(Link.destination),
            selectinload(Link.device_a_ref),
            selectinload(Link.device_b_ref)
        ).all()
        edges = []
        seen = set()
        for link in links:
            if not link.source_site or not link.destination_site:
                continue
            key = (link.source_site, link.destination_site)
            if key in seen:
                continue
            seen.add(key)
            last_check_str = link.last_checked.strftime("%Y-%m-%d %H:%M:%S") if link.last_checked else ""
            edge_label = ""
            if link.device_a_ref and link.device_b_ref:
                edge_label = f"{link.device_a_ref.hostname} \u2194 {link.device_b_ref.hostname}"
            edges.append({
                "data": {
                    "id": f"link-{link.id}",
                    "source": f"site-{link.source_site}",
                    "target": f"site-{link.destination_site}",
                    "label": edge_label,
                    "status": link.status,
                    "source_site_name": link.source.name if link.source else "",
                    "destination_site_name": link.destination.name if link.destination else "",
                    "device_a": link.device_a_ref.hostname if link.device_a_ref else "",
                    "device_a_ip": link.device_a_ref.ip if link.device_a_ref else "",
                    "device_a_model": link.device_a_ref.model if link.device_a_ref else "",
                    "device_b": link.device_b_ref.hostname if link.device_b_ref else "",
                    "device_b_ip": link.device_b_ref.ip if link.device_b_ref else "",
                    "device_b_model": link.device_b_ref.model if link.device_b_ref else "",
                    "last_checked": last_check_str
                }
            })

        elapsed = _time.perf_counter() - t0
        print(f"[DB] full_topology() -> {len(nodes)} sites, {len(edges)} edges, needs_layout={needs_layout} ({elapsed:.3f}s)")
        return {"nodes": nodes, "edges": edges, "needs_layout": needs_layout}
    finally:
        session.close()

def invalidate_topology_cache():
    print("[CACHE] topology cache invalidated (no-op)")

def location_topology():
    t0 = _time.perf_counter()
    print("[DB] location_topology()")
    session = SessionLocal()
    try:
        locations = session.query(Location).options(
            selectinload(Location.sites).selectinload(Site.devices)
        ).all()

        loc_nodes = []
        loc_count = len(locations)
        for idx, loc in enumerate(locations):
            total = 0
            down = 0
            for site in loc.sites:
                for d in site.devices:
                    total += 1
                    if not d.status:
                        down += 1
            if total == 0:
                status = "GREEN"
            elif down == total:
                status = "RED"
            elif down > 0:
                status = "YELLOW"
            else:
                status = "GREEN"
            loc_nodes.append({
                "data": {
                    "id": f"loc-{loc.id}",
                    "label": loc.name,
                    "status": status,
                    "type": "location",
                    "location_id": loc.id,
                    "device_count": total,
                    "down_count": down,
                    "site_count": len(loc.sites)
                },
                "position": {"x": float(idx * 2000), "y": 0.0}
            })

        # Collapsed inter-location edges with link counts
        links = session.query(Link).options(
            selectinload(Link.source),
            selectinload(Link.destination)
        ).all()
        loc_edges = []
        pair_counts = {}
        for link in links:
            src = link.source
            dst = link.destination
            if not src or not dst:
                continue
            if src.location_id == dst.location_id:
                continue
            key = tuple(sorted([src.location_id, dst.location_id]))
            if key not in pair_counts:
                src_loc = src.location
                dst_loc = dst.location
                pair_counts[key] = {
                    "src_loc_name": src_loc.name if src_loc else "",
                    "dst_loc_name": dst_loc.name if dst_loc else "",
                    "count": 0,
                    "status": True
                }
            pair_counts[key]["count"] += 1
            if not link.status:
                pair_counts[key]["status"] = False

        for (loc_a, loc_b), val in pair_counts.items():
            loc_edges.append({
                "data": {
                    "id": f"loc-edge-{loc_a}-{loc_b}",
                    "source": f"loc-{loc_a}",
                    "target": f"loc-{loc_b}",
                    "label": f"{val['src_loc_name']} \u2194 {val['dst_loc_name']} ({val['count']} links)",
                    "status": val['status']
                }
            })

        elapsed = _time.perf_counter() - t0
        print(f"[DB] location_topology() -> {len(loc_nodes)} locations, {len(loc_edges)} edges ({elapsed:.3f}s)")
        return {"nodes": loc_nodes, "edges": loc_edges}
    finally:
        session.close()

def location_sites(location_id):
    t0 = _time.perf_counter()
    print(f"[DB] location_sites(location_id={location_id})")
    session = SessionLocal()
    try:
        sites = session.query(Site).options(
            selectinload(Site.devices)
        ).filter(Site.location_id == location_id).all()
        positions = get_topology_positions()

        site_nodes = []
        for site in sites:
            total = len(site.devices)
            down = sum(1 for d in site.devices if not d.status)
            if total == 0:
                status = "GREEN"
            elif down == total:
                status = "RED"
            elif down > 0:
                status = "YELLOW"
            else:
                status = "GREEN"
            pos = positions.get(site.id)
            node = {
                "data": {
                    "id": f"site-{site.id}",
                    "label": site.name,
                    "status": status,
                    "type": "site",
                    "location_id": location_id,
                    "device_count": total,
                    "down_count": down
                }
            }
            if pos:
                node["position"] = {"x": pos["x"], "y": pos["y"]}
            site_nodes.append(node)

        # All links where source OR dest is in this location
        site_ids = [s.id for s in sites]
        all_links = session.query(Link).options(
            selectinload(Link.source),
            selectinload(Link.destination),
            selectinload(Link.device_a_ref),
            selectinload(Link.device_b_ref)
        ).filter(
            (Link.source_site.in_(site_ids)) | (Link.destination_site.in_(site_ids))
        ).all()

        edges = []
        seen = set()
        for link in all_links:
            if not link.source_site or not link.destination_site:
                continue
            key = (link.source_site, link.destination_site)
            if key in seen:
                continue
            seen.add(key)
            last_check_str = link.last_checked.strftime("%Y-%m-%d %H:%M:%S") if link.last_checked else ""
            edge_label = ""
            if link.device_a_ref and link.device_b_ref:
                edge_label = f"{link.device_a_ref.hostname} \u2194 {link.device_b_ref.hostname}"
            edges.append({
                "data": {
                    "id": f"link-{link.id}",
                    "source": f"site-{link.source_site}",
                    "target": f"site-{link.destination_site}",
                    "label": edge_label,
                    "status": link.status,
                    "source_site_name": link.source.name if link.source else "",
                    "destination_site_name": link.destination.name if link.destination else "",
                    "source_location_id": link.source.location_id if link.source else None,
                    "destination_location_id": link.destination.location_id if link.destination else None,
                    "device_a": link.device_a_ref.hostname if link.device_a_ref else "",
                    "device_a_ip": link.device_a_ref.ip if link.device_a_ref else "",
                    "device_a_model": link.device_a_ref.model if link.device_a_ref else "",
                    "device_b": link.device_b_ref.hostname if link.device_b_ref else "",
                    "device_b_ip": link.device_b_ref.ip if link.device_b_ref else "",
                    "device_b_model": link.device_b_ref.model if link.device_b_ref else "",
                    "last_checked": last_check_str
                }
            })

        elapsed = _time.perf_counter() - t0
        print(f"[DB] location_sites({location_id}) -> {len(site_nodes)} sites, {len(edges)} edges ({elapsed:.3f}s)")
        return {"nodes": site_nodes, "edges": edges}
    finally:
        session.close()

def site_devices(site_id):
    t0 = _time.perf_counter()
    print(f"[DB] site_devices(site_id={site_id})")
    session = SessionLocal()
    try:
        devices = session.query(Device).filter(Device.site_id == site_id).all()
        site_pos = session.query(TopologyNode).filter(
            TopologyNode.site_id == site_id
        ).first()
        base_x = site_pos.x_percent if site_pos else 0.0
        base_y = site_pos.y_percent if site_pos else 0.0

        dev_count = len(devices)
        cols = max(1, DEVICE_COLS)
        nodes = []
        for i, d in enumerate(devices):
            row = i // cols
            col = i % cols
            x = base_x + col * DEVICE_SPACING_X - (min(dev_count, cols) - 1) * DEVICE_SPACING_X / 2
            y = base_y + 50 + row * DEVICE_SPACING_Y
            nodes.append({
                "data": {
                    "id": f"device-{d.id}",
                    "label": d.hostname,
                    "status": d.status,
                    "type": "device",
                    "ip": d.ip,
                    "model": d.model,
                    "category": d.category,
                    "site_id": site_id
                },
                "position": {"x": float(x), "y": float(y)}
            })
        elapsed = _time.perf_counter() - t0
        print(f"[DB] site_devices({site_id}) -> {len(nodes)} devices ({elapsed:.3f}s)")
        return {"nodes": nodes}
    finally:
        session.close()

def get_all_sites():
    print("[DB] get_all_sites()")
    session=SessionLocal()
    try:
        sites=session.query(Site).options(selectinload(Site.location),selectinload(Site.devices)).all()
        print(f"[DB] get_all_sites() -> {len(sites)} sites")
        return sites
    finally:
        session.close()

def get_all_locations():
    print("[DB] get_all_locations()")
    session=SessionLocal()
    try:
        locs=session.query(Location).options(selectinload(Location.sites)).all()
        print(f"[DB] get_all_locations() -> {len(locs)} locations")
        return locs
    finally:
        session.close()

def add_location(name):
    print(f"[DB] add_location(name={name})")
    session=SessionLocal()
    try:
        existing=session.query(Location).filter(Location.name==name).first()
        if existing:
            print(f"[DB] add_location({name}) -> already exists")
            return False
        location=Location(name=name)
        session.add(location)
        session.commit()
        print(f"[DB] add_location({name}) -> id={location.id}")
        return location
    except Exception as e:
        session.rollback()
        print(f"[DB] add_location({name}) -> error: {e}")
        return e
    finally:
        session.close()

def add_site(name, location_id):
    print(f"[DB] add_site(name={name}, location_id={location_id})")
    session=SessionLocal()
    try:
        existing=session.query(Site).filter(Site.name==name, Site.location_id==location_id).first()
        if existing:
            print(f"[DB] add_site({name}) -> already exists")
            return False
        site=Site(name=name, location_id=location_id)
        session.add(site)
        session.commit()
        print(f"[DB] add_site({name}) -> id={site.id}")
        invalidate_topology_cache()
        return site
    except Exception as e:
        session.rollback()
        print(f"[DB] add_site({name}) -> error: {e}")
        return e
    finally:
        session.close()

def add_device(hostname, ip, model, category, site_id):
    print(f"[DB] add_device(hostname={hostname}, ip={ip}, model={model}, category={category}, site_id={site_id})")
    session=SessionLocal()
    try:
        device=Device(hostname=hostname, ip=ip, model=model, category=category, site_id=site_id)
        session.add(device)
        session.commit()
        print(f"[DB] add_device({hostname}) -> id={device.id}")
        invalidate_topology_cache()
        return device
    except Exception as e:
        session.rollback()
        print(f"[DB] add_device({hostname}) -> error: {e}")
        return e
    finally:
        session.close()

def add_link(source_site_id, dest_site_id, device_a_id=None, device_b_id=None):
    print(f"[DB] add_link(source={source_site_id}, dest={dest_site_id})")
    session=SessionLocal()
    try:
        link=Link(source_site=source_site_id, destination_site=dest_site_id,
                  device_a=device_a_id, device_b=device_b_id)
        session.add(link)
        session.commit()
        print(f"[DB] add_link() -> id={link.id}")
        invalidate_topology_cache()
        return link
    except Exception as e:
        session.rollback()
        print(f"[DB] add_link() -> error: {e}")
        return e
    finally:
        session.close()

def get_topology_positions():
    print("[DB] get_topology_positions()")
    session=SessionLocal()
    try:
        nodes=session.query(TopologyNode).all()
        result = {n.site_id: {"x": n.x_percent, "y": n.y_percent, "pinned": n.pinned, "priority": n.priority} for n in nodes}
        print(f"[DB] get_topology_positions() -> {len(result)} entries")
        return result
    finally:
        session.close()

def save_topology_position(site_id, x_percent, y_percent, pinned=False):
    print(f"[DB] save_topology_position(site_id={site_id}, x={x_percent}, y={y_percent})")
    session=SessionLocal()
    try:
        node=session.query(TopologyNode).filter(TopologyNode.site_id==site_id).first()
        if node:
            print(f"[DB]   updating existing topology_nodes row id={node.id}")
            node.x_percent=x_percent
            node.y_percent=y_percent
            node.pinned=pinned
        else:
            print(f"[DB]   inserting new topology_nodes row")
            node=TopologyNode(site_id=site_id, x_percent=x_percent, y_percent=y_percent, pinned=pinned)
            session.add(node)
        session.commit()
        print("[DB]   save OK")
        return True
    except Exception as e:
        session.rollback()
        print(f"[DB]   save error: {e}")
        return e
    finally:
        session.close()

def auto_place_site(site_id):
    print(f"[DB] auto_place_site(site_id={site_id})")
    session=SessionLocal()
    try:
        existing=session.query(TopologyNode).filter(TopologyNode.site_id==site_id).first()
        if existing:
            return existing
        # find linked sites that already have positions
        links=session.query(Link).filter(
            (Link.source_site==site_id) | (Link.destination_site==site_id)
        ).all()
        placed=session.query(TopologyNode).all()
        if placed:
            # place near the average of connected placed sites
            xs, ys = [], []
            for link in links:
                other_id = link.destination_site if link.source_site==site_id else link.source_site
                pos = next((p for p in placed if p.site_id==other_id), None)
                if pos:
                    xs.append(pos.x_percent)
                    ys.append(pos.y_percent)
            if xs:
                x = sum(xs)/len(xs) + 5
                y = sum(ys)/len(ys) + 5
            else:
                avg_x = sum(p.x_percent for p in placed)/len(placed)
                avg_y = sum(p.y_percent for p in placed)/len(placed)
                x = avg_x + 10
                y = avg_y + 10
        else:
            x, y = 50.0, 50.0
        node=TopologyNode(site_id=site_id, x_percent=x, y_percent=y)
        session.add(node)
        session.commit()
        return node
    except Exception as e:
        session.rollback()
        return e
    finally:
        session.close()

def update_location(location_id, name):
    session=SessionLocal()
    try:
        loc=session.get(Location, location_id)
        if not loc:
            return False
        loc.name=name
        session.commit()
        return loc
    except Exception as e:
        session.rollback()
        return e
    finally:
        session.close()

def delete_location(location_id):
    session=SessionLocal()
    try:
        loc=session.get(Location, location_id)
        if not loc:
            return False
        session.delete(loc)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        return e
    finally:
        session.close()

def update_site(site_id, name, location_id):
    session=SessionLocal()
    try:
        site=session.get(Site, site_id)
        if not site:
            return False
        site.name=name
        site.location_id=location_id
        session.commit()
        return site
    except Exception as e:
        session.rollback()
        return e
    finally:
        session.close()

def delete_site(site_id):
    session=SessionLocal()
    try:
        site=session.get(Site, site_id)
        if not site:
            return False
        session.delete(site)
        session.commit()
        print(f"[DB] delete_site({site_id}) -> ok")
        invalidate_topology_cache()
        return True
    except Exception as e:
        session.rollback()
        return e
    finally:
        session.close()

def get_all_devices():
    print("[DB] get_all_devices()")
    session=SessionLocal()
    try:
        devs=session.query(Device).options(selectinload(Device.site).selectinload(Site.location)).all()
        print(f"[DB] get_all_devices() -> {len(devs)} devices")
        return devs
    finally:
        session.close()

def update_device(device_id, hostname, ip, model, category, site_id):
    session=SessionLocal()
    try:
        dev=session.get(Device, device_id)
        if not dev:
            return False
        dev.hostname=hostname
        dev.ip=ip
        dev.model=model
        dev.category=category
        dev.site_id=site_id
        session.commit()
        return dev
    except Exception as e:
        session.rollback()
        return e
    finally:
        session.close()

def delete_device(device_id):
    session=SessionLocal()
    try:
        dev=session.get(Device, device_id)
        if not dev:
            return False
        session.delete(dev)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        return e
    finally:
        session.close()

def get_details_paginated(page=1, per_page=20, sort_by="id", sort_dir="asc"):
    session=SessionLocal()
    try:
        q = session.query(Device).options(
            selectinload(Device.site).selectinload(Site.location)
        )
        total = q.count()
        sort_map = {
            "location": Site.location_id,
            "site": Site.name,
            "hostname": Device.hostname,
            "ip": Device.ip,
            "model": Device.model,
            "category": Device.category,
            "status": Device.status,
        }
        col = sort_map.get(sort_by, Device.id)
        if sort_dir == "desc":
            col = col.desc()
        else:
            col = col.asc()
        if sort_by in ("location", "site"):
            q = q.join(Site)
            col = sort_map[sort_by]
            if sort_dir == "desc":
                col = col.desc()
        devices = q.order_by(col, Device.id).offset((page-1)*per_page).limit(per_page).all()
        rows=[]
        for d in devices:
            rows.append({
                "location": d.site.location.name if d.site and d.site.location else "",
                "site": d.site.name if d.site else "",
                "hostname": d.hostname,
                "ip": d.ip,
                "model": d.model,
                "category": d.category,
                "status": "Up" if d.status else "Down"
            })
        return rows, total
    finally:
        session.close()

def add_devices_bulk(devices_data):
    session=SessionLocal()
    added=[]
    errors=[]
    try:
        for d in devices_data:
            existing=session.query(Device).filter(
                (Device.hostname==d["hostname"]) | (Device.ip==d["ip"])
            ).first()
            if existing:
                errors.append(f"Duplicate hostname/IP: {d['hostname']}/{d['ip']}")
                continue
            device=Device(
                hostname=d["hostname"],
                ip=d["ip"],
                model=d["model"],
                category=d["category"],
                site_id=d["site_id"]
            )
            session.add(device)
            added.append(device)
        session.commit()
    except Exception as e:
        session.rollback()
        return [], [str(e)]
    finally:
        session.close()
    return added, errors

def all_devices_status():
    session = SessionLocal()
    try:
        devices = session.query(Device).options(
            selectinload(Device.site).selectinload(Site.location)
        ).all()
        result = []
        for device in devices:
            last_seen_str = device.last_seen.strftime("%Y-%m-%d %H:%M:%S") if device.last_seen else None
            result.append({
                "id": str(device.id),
                "label": device.hostname,
                "ip": device.ip,
                "status": device.status,
                "category": device.category,
                "site": device.site.name,
                "location": device.site.location.name,
                "last_seen": last_seen_str
            })
        return result
    finally:
        session.close()

import json
import math

LOCATION_GRID_X = 0
SITE_SPACING_X = 280
SITE_SPACING_Y = 200
SITE_COLS = 4
DEVICE_SPACING_X = 120
DEVICE_SPACING_Y = 80
DEVICE_COLS = 5

def generate_grid_positions():
    t0 = _time.perf_counter()
    print("[DB] generate_grid_positions()")
    session = SessionLocal()
    try:
        locations = session.query(Location).order_by(Location.id).all()
        count = 0
        for loc_idx, loc in enumerate(locations):
            loc_x = loc_idx * 2000
            sites = session.query(Site).filter(
                Site.location_id == loc.id
            ).order_by(Site.name).all()
            for idx, site in enumerate(sites):
                row = idx // SITE_COLS
                col = idx % SITE_COLS
                x = loc_x + col * SITE_SPACING_X
                y = row * SITE_SPACING_Y
                existing = session.query(TopologyNode).filter(
                    TopologyNode.site_id == site.id
                ).first()
                if existing:
                    existing.x_percent = float(x)
                    existing.y_percent = float(y)
                else:
                    node = TopologyNode(
                        site_id=site.id,
                        x_percent=float(x),
                        y_percent=float(y)
                    )
                    session.add(node)
                count += 1
        session.commit()
        elapsed = _time.perf_counter() - t0
        print(f"[DB] generate_grid_positions() -> {count} positions set ({elapsed:.3f}s)")
        return {"ok": True, "count": count}
    except Exception as e:
        session.rollback()
        print(f"[DB] generate_grid_positions() -> error: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        session.close()

def build_heartbeat_paths():
    t0 = _time.perf_counter()
    print("[DB] build_heartbeat_paths()")
    session = SessionLocal()
    try:
        links = session.query(Link).options(
            selectinload(Link.source),
            selectinload(Link.destination),
            selectinload(Link.device_a_ref),
            selectinload(Link.device_b_ref)
        ).filter(Link.status == True).all()

        link_map = {}
        for link in links:
            if link.device_a_ref and link.device_b_ref:
                a_id = f"device-{link.device_a_ref.id}"
                b_id = f"device-{link.device_b_ref.id}"
                link_id = f"link-{link.id}"
                link_map.setdefault(a_id, []).append({
                    "target": b_id,
                    "link_id": link_id,
                    "status": link.status,
                    "source_site": link.source_site,
                    "destination_site": link.destination_site
                })
                link_map.setdefault(b_id, []).append({
                    "target": a_id,
                    "link_id": link_id,
                    "status": link.status,
                    "source_site": link.destination_site,
                    "destination_site": link.source_site
                })

        paths = []
        used_devices = set()
        for link in links[:20]:
            if not link.device_a_ref or not link.device_b_ref:
                continue
            start = f"device-{link.device_a_ref.id}"
            if start in used_devices:
                continue
            path_devices = [start]
            path_links = [f"link-{link.id}"]
            current = f"device-{link.device_b_ref.id}"
            path_devices.append(current)
            used_devices.add(start)

            max_hops = 8
            for _ in range(max_hops):
                neighbors = link_map.get(current, [])
                found = False
                for nb in neighbors:
                    if nb["target"] not in path_devices:
                        path_devices.append(nb["target"])
                        path_links.append(nb["link_id"])
                        current = nb["target"]
                        found = True
                        break
                if not found:
                    break

            if len(path_devices) >= 2:
                paths.append({
                    "id": f"path-{len(paths)+1}",
                    "name": f"{path_devices[0]} → {path_devices[-1]}",
                    "source_device": path_devices[0],
                    "destination_device": path_devices[-1],
                    "route_devices": path_devices,
                    "route_links": path_links
                })

        elapsed = _time.perf_counter() - t0
        print(f"[DB] build_heartbeat_paths() -> {len(paths)} paths ({elapsed:.3f}s)")
        return {"paths": paths}
    finally:
        session.close()

def topology_paths():
    return build_heartbeat_paths()


def cache_topology(key, data):
    from db.models import TopologyCache
    from datetime import datetime
    session = SessionLocal()
    try:
        existing = session.query(TopologyCache).filter(TopologyCache.key == key).first()
        serialized = json.dumps(data)
        if existing:
            existing.data = serialized
            existing.created_at = datetime.now(timezone.utc).replace(tzinfo=None)
        else:
            entry = TopologyCache(key=key, data=serialized)
            session.add(entry)
        session.commit()
        print(f"[DB] cache_topology({key}) -> cached")
    finally:
        session.close()

def get_cached_topology(key, ttl=10):
    from db.models import TopologyCache
    from datetime import datetime, timezone
    session = SessionLocal()
    try:
        existing = session.query(TopologyCache).filter(TopologyCache.key == key).first()
        if existing and (datetime.now(timezone.utc).replace(tzinfo=None) - existing.created_at).total_seconds() < ttl:
            print(f"[DB] get_cached_topology({key}) -> cache HIT")
            return json.loads(existing.data)
        print(f"[DB] get_cached_topology({key}) -> cache MISS/EXPIRED")
        return None
    finally:
        session.close()

def invalidate_cache_for(key_prefix):
    from db.models import TopologyCache
    session = SessionLocal()
    try:
        session.query(TopologyCache).filter(TopologyCache.key.like(f"{key_prefix}%")).delete()
        session.commit()
        print(f"[DB] invalidate_cache({key_prefix}) -> invalidated")
    finally:
        session.close()

