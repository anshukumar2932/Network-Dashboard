from sqlalchemy.orm import sessionmaker, selectinload
from sqlalchemy.exc import IntegrityError
from db.models import engine, User, Device, NetworkLink, PingHistory, TopologyCache, Category, DashboardState
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import select, func, or_
from datetime import datetime, timezone
import time as _time
import json
import re

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

IP_RE = re.compile(
    r'^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$'
)


def _get_or_create_category(session, name):
    name = name.strip().lower()
    cat = session.query(Category).filter(Category.name == name).first()
    if not cat:
        cat = Category(name=name)
        session.add(cat)
        session.flush()
    return cat


def login(username, password):
    print(f"[DB] login(username={username})")
    session = SessionLocal()
    try:
        user = session.query(User).filter_by(user=username).first()
        if user and check_password_hash(user.passwd, password):
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

def all_devices_status():
    session = SessionLocal()
    try:
        devices = session.query(Device).all()
        result = []
        for device in devices:
            last_seen_str = device.last_seen.strftime("%Y-%m-%d %H:%M:%S") if device.last_seen else None
            result.append({
                "id": device.ip,
                "label": device.device_name or device.ip,
                "ip": device.ip,
                "status": device.status,
                "category": device.category_obj.name if device.category_obj else "",
                "location": device.location or "",
                "device_name": device.device_name or "",
                "hostname": device.hostname or "",
                "model": device.model or "",
                "last_seen": last_seen_str
            })
        return result
    finally:
        session.close()


def add_device(device_name, ip, model, category, location):
    print(f"[DB] add_device(device_name={device_name}, ip={ip})")
    session = SessionLocal()
    try:
        existing = session.query(Device).filter(Device.ip == ip).first()
        if existing:
            print(f"[DB] add_device({ip}) -> already exists")
            return False
        cat = _get_or_create_category(session, category)
        device = Device(
            ip=ip,
            hostname=device_name,
            device_name=device_name,
            model=model,
            category_id=cat.id,
            location=location
        )
        session.add(device)
        session.commit()
        print(f"[DB] add_device({ip}) -> ok")
        return device
    except Exception as e:
        session.rollback()
        print(f"[DB] add_device({ip}) -> error: {e}")
        return e
    finally:
        session.close()


def update_device(ip, device_name=None, model=None, category=None, location=None):
    session = SessionLocal()
    try:
        dev = session.query(Device).filter(Device.ip == ip).first()
        if not dev:
            return False
        if device_name is not None:
            dev.device_name = device_name
            if not dev.hostname:
                dev.hostname = device_name
        if model is not None:
            dev.model = model
        if category is not None:
            cat = _get_or_create_category(session, category)
            dev.category_id = cat.id
        if location is not None:
            dev.location = location
        session.commit()
        return dev
    except Exception as e:
        session.rollback()
        return e
    finally:
        session.close()


def delete_device(ip):
    session = SessionLocal()
    try:
        dev = session.query(Device).filter(Device.ip == ip).first()
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


def add_devices_bulk(devices_data):
    session = SessionLocal()
    added = []
    errors = []
    try:
        for d in devices_data:
            existing = session.query(Device).filter(Device.ip == d["ip"]).first()
            if existing:
                errors.append(f"Duplicate IP: {d['ip']}")
                continue
            dn = d.get("device_name", d.get("hostname", ""))
            cat = _get_or_create_category(session, d.get("category", "radio"))
            device = Device(
                ip=d["ip"],
                hostname=dn,
                device_name=dn,
                model=d.get("model", ""),
                category_id=cat.id,
                location=d.get("location", "")
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


def add_link(source_ip, destination_ip, remark=None, status=True, link_type=None, bandwidth=None):
    print(f"[DB] add_link(source={source_ip}, dest={destination_ip})")
    session = SessionLocal()
    try:
        existing = (
            session.query(NetworkLink)
            .filter(
                NetworkLink.source_ip == source_ip,
                NetworkLink.destination_ip == destination_ip,
            )
            .first()
        )
        if existing:
            print(f"[DB] add_link() -> duplicate rejected")
            return None
        link = NetworkLink(
            source_ip=source_ip,
            destination_ip=destination_ip,
            remark=remark,
            status=status,
            link_type=link_type,
            bandwidth=bandwidth
        )
        session.add(link)
        session.commit()
        print(f"[DB] add_link() -> id={link.id}")
        return link
    except Exception as e:
        session.rollback()
        print(f"[DB] add_link() -> error: {e}")
        return e
    finally:
        session.close()


def get_details_paginated(page=1, per_page=20, sort_by="ip", sort_dir="asc", search=""):
    session = SessionLocal()
    try:
        q = session.query(Device)
        if search:
            s = f"%{search}%"
            q = q.filter(or_(
                Device.ip.like(s),
                Device.device_name.like(s),
                Device.model.like(s),
                Device.location.like(s),
            ))
        total = q.count()
        sort_map = {
            "ip": Device.ip,
            "device_name": Device.device_name,
            "location": Device.location,
            "model": Device.model,
            "status": Device.status,
        }
        if sort_by == "category":
            q = q.join(Category)
            col = Category.name
        else:
            col = sort_map.get(sort_by, Device.ip)
        if sort_dir == "desc":
            col = col.desc()
        devices = q.order_by(col).offset((page - 1) * per_page).limit(per_page).all()
        rows = []
        for d in devices:
            last_seen_str = d.last_seen.strftime("%Y-%m-%d %H:%M:%S") if d.last_seen else None
            rows.append({
                "ip": d.ip,
                "device_name": d.device_name,
                "hostname": d.hostname or "",
                "location": d.location,
                "model": d.model,
                "category": d.category_obj.name if d.category_obj else "",
                "status": d.status,
                "last_seen": last_seen_str,
            })
        return rows, total
    finally:
        session.close()


def derive_node_status(ip, links, device_up=None):
    if device_up is False:
        return "RED", False
    return "GREEN", True


def get_ip_topology():
    t0 = _time.perf_counter()
    print("[DB] get_ip_topology()")
    session = SessionLocal()
    try:
        devices = session.query(Device).all()
        device_map = {d.ip: d for d in devices}
        device_ids = {d.category_id for d in devices}
        device_ips = [d.ip for d in devices]

        # Fetch all links where either endpoint is a known device
        links = session.query(NetworkLink).options(
            selectinload(NetworkLink.source_device),
            selectinload(NetworkLink.destination_device)
        ).filter(
            or_(
                NetworkLink.source_ip.in_(device_ips),
                NetworkLink.destination_ip.in_(device_ips)
            )
        ).all()

        links = [l for l in links
                 if l.source_device
                 and l.source_device.category_id in device_ids]

        print(f"[DB] {len(links)} links fetched")
        for l in links:
            print(f"  LINK id={l.id} | {l.source_ip} -> {l.destination_ip} | status={l.status}")

        location_groups = {}
        for d in devices:
            loc = d.location or "Unknown"
            location_groups.setdefault(loc, []).append(d.ip)

        nodes = []
        loc_index = 0
        loc_cols = 4
        for loc, ips in location_groups.items():
            base_x = (loc_index % loc_cols) * 600
            base_y = (loc_index // loc_cols) * 500
            for i, ip in enumerate(ips):
                d = device_map.get(ip)
                node_status, status_bool = derive_node_status(ip, links, device_up=d.status if d else None)
                print(f"[DB] {ip} device_up={d.status if d else None} -> status={node_status}")
                nodes.append({
                    "data": {
                        "id": ip,
                        "label": d.hostname or d.device_name or ip,
                        "status": node_status,
                        "status_bool": status_bool,
                        "location": loc,
                        "type": "device",
                        "device_name": d.device_name if d else "",
                        "hostname": d.hostname if d else "",
                        "model": d.model if d else "",
                        "category": d.category_obj.name if d and d.category_obj else "radio",
                        "remark": d.remark if d else "",
                        "tooltip": ip
                    },
                    "position": {
                        "x": float(base_x + 150 * 1.5 + 150 * 1.5 * (i % 2)),
                        "y": float(base_y + 80 + (i // 2) * 120)
                    }
                })
            loc_index += 1

        # Category hierarchy
        CATEGORY_HIERARCHY = {
            "core": 0,
            "distribution": 1,
            "switch": 1,
            "access": 2,
            "ap": 3,
            "access point": 3,
            "camera": 3,
            "end device": 4,
            "radio": 2,
        }

        def get_category_tier(cat_name):
            if not cat_name:
                return 5
            return CATEGORY_HIERARCHY.get(cat_name.lower().strip(), 5)

        device_tier = {}
        for n in nodes:
            ip = n["data"]["id"]
            cat = n["data"].get("category", "")
            tier = get_category_tier(cat)
            device_tier[ip] = tier
            n["data"]["level"] = tier
            n["data"]["role"] = cat.lower().strip() if cat else "unknown"

        print("[DB] Tier assignments:")
        for ip, tier in device_tier.items():
            d = device_map.get(ip)
            cat = d.category_obj.name if d and d.category_obj else "?"
            print(f"  {ip} | category={cat} | tier={tier}")

        edges = []
        for link in links:
            if not link.destination_ip:
                continue

            src_ip = link.source_ip
            tgt_ip = link.destination_ip
            src = device_map.get(src_ip)
            dst = device_map.get(tgt_ip)
            src_tier = device_tier.get(src_ip, 5)
            tgt_tier = device_tier.get(tgt_ip, 5)

            # Relationship by tier — never flip source/target, respect DB direction
            if src_tier < tgt_tier:
                relationship = "child"
            elif src_tier == tgt_tier:
                relationship = "link"
            else:
                relationship = "child"  # reverse direction child, kept as-is

            # Status: always "true"/"false" string for Cytoscape CSS selectors
            status_str = "true" if link.status else "false"

            last_check_str = link.last_checked.strftime("%Y-%m-%d %H:%M:%S") if link.last_checked else ""

            edge = {
                "data": {
                    "id": f"link-{link.id}",
                    "source": src_ip,
                    "target": tgt_ip,
                    "label": link.remark or "",
                    "status": status_str,          # "true" = green, "false" = red
                    "relationship": relationship,
                    "link_type": link.link_type or "",
                    "bandwidth": link.bandwidth or "",
                    "source_location": src.location if src else "",
                    "destination_location": dst.location if dst else "",
                    "source_device_name": src.device_name if src else "",
                    "destination_device_name": dst.device_name if dst else "",
                    "last_checked": last_check_str,
                    "latency_ms": link.latency_ms,
                }
            }
            edges.append(edge)

            print(f"  EDGE id=link-{link.id} | {src_ip}(t{src_tier}) -> {tgt_ip}(t{tgt_tier}) | rel={relationship} | status={status_str}")

        elapsed = _time.perf_counter() - t0
        print(f"[DB] get_ip_topology() -> DONE: {len(nodes)} nodes, {len(edges)} edges ({elapsed:.3f}s)")
        return {"nodes": nodes, "edges": edges}
    finally:
        session.close()
# Backward-compatible alias
get_topology = get_ip_topology


def get_locations():
    print("[DB] get_locations()")
    session = SessionLocal()
    try:
        rows = session.query(Device.location, func.count(Device.ip)).group_by(Device.location).all()
        result = []
        for loc, count in rows:
            total = count
            down = session.query(Device).filter(Device.location == loc, Device.status == False).count()
            result.append({
                "name": loc,
                "device_count": total,
                "down_count": down,
                "status": "GREEN" if down == 0 else ("RED" if down == total else "YELLOW")
            })
        print(f"[DB] get_locations() -> {len(result)} locations")
        return result
    finally:
        session.close()


def get_location_devices(location_name):
    print(f"[DB] get_location_devices(location_name={location_name})")
    session = SessionLocal()
    try:
        devices = session.query(Device).filter(Device.location == location_name).all()
        return [
            {
                "ip": d.ip,
                "device_name": d.device_name,
                "model": d.model,
                "category": d.category_obj.name if d.category_obj else "",
                "status": d.status
            }
            for d in devices
        ]
    finally:
        session.close()


def get_location_links(location_name):
    print(f"[DB] get_location_links(location_name={location_name})")
    session = SessionLocal()
    try:
        devices = session.query(Device.ip).filter(Device.location == location_name).all()
        ips = [d[0] for d in devices]
        links = session.query(NetworkLink).options(
            selectinload(NetworkLink.source_device),
            selectinload(NetworkLink.destination_device)
        ).filter(
            (NetworkLink.source_ip.in_(ips)) | (NetworkLink.destination_ip.in_(ips))
        ).all()
        return [
            {
                "id": link.id,
                "source_ip": link.source_ip,
                "destination_ip": link.destination_ip,
                "status": link.status,
                "remark": link.remark,
                "source_device_name": link.source_device.device_name if link.source_device else "",
                "destination_device_name": link.destination_device.device_name if link.destination_device else "",
                "source_location": link.source_device.location if link.source_device else "",
                "destination_location": link.destination_device.location if link.destination_device else ""
            }
            for link in links
        ]
    finally:
        session.close()


def get_device_by_ip(ip):
    session = SessionLocal()
    try:
        return session.query(Device).filter(Device.ip == ip).first()
    finally:
        session.close()


def get_links_for_device(ip):
    session = SessionLocal()
    try:
        cat_names = set(category_list())
        links = session.query(NetworkLink).options(
            selectinload(NetworkLink.source_device),
            selectinload(NetworkLink.destination_device)
        ).filter(
            (NetworkLink.source_ip == ip) | (NetworkLink.destination_ip == ip)
        ).all()
        result = []
        for link in links:
            src = link.source_device
            if not src:
                continue
            src_cat = src.category_obj.name if src.category_obj else ""
            if src_cat not in cat_names:
                continue
            if link.source_ip == ip:
                other = link.destination_device
            else:
                other = src
            result.append({
                "id": link.id,
                "other_ip": other.ip if other else "",
                "other_device_name": other.device_name if other else "",
                "other_location": other.location if other else "",
                "status": link.status,
                "remark": link.remark
            })
        return result
    finally:
        session.close()


def get_devices_stats():
    session = SessionLocal()
    try:
        stats = []
        total = 0
        total_up = 0
        for cat_obj in session.query(Category).all():
            cnt = session.query(Device).filter(Device.category_id == cat_obj.id).count()
            up = session.query(Device).filter(Device.category_id == cat_obj.id, Device.status == True).count()
            down = cnt - up
            total += cnt
            total_up += up
            stats.append({"category": cat_obj.name, "total": cnt, "up": up, "down": down})
        return {"categories": stats, "total": total, "up": total_up, "down": total - total_up}
    finally:
        session.close()


def get_all_links():
    session = SessionLocal()
    try:
        links = session.query(NetworkLink).options(
            selectinload(NetworkLink.source_device),
            selectinload(NetworkLink.destination_device)
        ).all()
        return [
            {
                "id": link.id,
                "source_ip": link.source_ip,
                "destination_ip": link.destination_ip,
                "link_type": link.link_type,
                "status": link.status,
                "latency_ms": link.latency_ms,
                "bandwidth": link.bandwidth,
                "remark": link.remark,
                "source_device_name": link.source_device.device_name if link.source_device else "",
                "destination_device_name": link.destination_device.device_name if link.destination_device else "",
                "source_location": link.source_device.location if link.source_device else "",
                "destination_location": link.destination_device.location if link.destination_device else ""
            }
            for link in links
        ]
    finally:
        session.close()


def get_links_paginated(page=1, per_page=20, search_ip="", filter_status="",
                        filter_category="", filter_location="",
                        sort_by="id", sort_order="desc"):
    """
    Returns (links_list, total_count, total_pages) with server-side filtering, sorting and pagination.

    Filters:
      search_ip       – substring match against source_ip OR destination_ip
      filter_status   – "up" | "down" | "" (all)
      filter_category – device category on either endpoint ("radio", "ap", etc.)
      filter_location – location string on either endpoint
    Sort:
      sort_by    – column key (id, source_ip, destination_ip, source_location,
                   destination_location, remark, status)
      sort_order – "asc" or "desc"
    """
    from sqlalchemy.orm import aliased

    _SORT_MAP = {
        "id": NetworkLink.id,
        "source_ip": NetworkLink.source_ip,
        "destination_ip": NetworkLink.destination_ip,
        "remark": NetworkLink.remark,
        "status": NetworkLink.status,
    }

    session = SessionLocal()
    try:
        SrcDev = aliased(Device, name="src_dev")
        DstDev = aliased(Device, name="dst_dev")

        _SORT_MAP["source_location"] = SrcDev.location
        _SORT_MAP["destination_location"] = DstDev.location

        q = (
            session.query(NetworkLink)
            .join(SrcDev, NetworkLink.source_ip == SrcDev.ip)
            .outerjoin(DstDev, NetworkLink.destination_ip == DstDev.ip)
        )

        if filter_category:
            q = q.join(Category, Category.name == filter_category)
            q = q.filter(
                or_(
                    SrcDev.category_id == Category.id,
                    DstDev.category_id == Category.id,
                    DstDev.ip == None,
                )
            )

        # IP search – matches source or destination
        if search_ip:
            s = f"%{search_ip}%"
            q = q.filter(or_(
                NetworkLink.source_ip.like(s),
                NetworkLink.destination_ip.like(s),
                SrcDev.device_name.like(s),
                DstDev.device_name.like(s),
            ))

        # Status filter
        if filter_status == "up":
            q = q.filter(NetworkLink.status == True)
        elif filter_status == "down":
            q = q.filter(NetworkLink.status == False)

        # Location filter (either endpoint)
        if filter_location:
            q = q.filter(or_(
                SrcDev.location == filter_location,
                DstDev.location == filter_location,
            ))

        total = q.count()

        sort_col = _SORT_MAP.get(sort_by, NetworkLink.id)
        if sort_order == "asc":
            q = q.order_by(sort_col.asc().nullslast())
        else:
            q = q.order_by(sort_col.desc().nullsfirst())

        links = (
            q.offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        rows = []
        for link in links:
            src = link.source_device
            dst = link.destination_device
            rows.append({
                "id": link.id,
                "source_ip": link.source_ip,
                "destination_ip": link.destination_ip,
                "link_type": link.link_type or "",
                "status": link.status,
                "latency_ms": link.latency_ms,
                "bandwidth": link.bandwidth or "",
                "remark": link.remark or "",
                "source_device_name": src.device_name if src else "",
                "source_hostname": src.hostname if src else "",
                "source_category": src.category_obj.name if src and src.category_obj else "",
                "source_location": src.location if src else "",
                "source_model": src.model if src else "",
                "destination_device_name": dst.device_name if dst else "",
                "destination_hostname": dst.hostname if dst else "",
                "destination_category": dst.category_obj.name if dst and dst.category_obj else "",
                "destination_location": dst.location if dst else "",
                "destination_model": dst.model if dst else "",
            })

        total_pages = max(1, (total + per_page - 1) // per_page)
        return rows, total, total_pages

    finally:
        session.close()


def get_link_filter_options():
    """Returns distinct categories and locations present in linked devices."""
    session = SessionLocal()
    try:
        linked_ips = select(NetworkLink.source_ip).union(select(NetworkLink.destination_ip)).scalar_subquery()
        rows = (
            session.query(Category.name, Device.location)
            .join(Device, Device.category_id == Category.id)
            .filter(Device.ip.in_(select(linked_ips)))
            .distinct()
            .all()
        )
        categories = sorted({r[0] for r in rows if r[0]})
        locations = sorted({r[1] for r in rows if r[1]})
        return categories, locations
    finally:
        session.close()


def update_link(link_id, source_ip=None, destination_ip=None, link_type=None, status=None, bandwidth=None, remark=None):
    session = SessionLocal()
    try:
        link = session.get(NetworkLink, link_id)
        if not link:
            return None
        if source_ip is not None:
            link.source_ip = source_ip
        if destination_ip is not None:
            link.destination_ip = destination_ip
        if link_type is not None:
            link.link_type = link_type
        if status is not None:
            link.status = status
        if bandwidth is not None:
            link.bandwidth = bandwidth
        if remark is not None:
            link.remark = remark
        session.commit()
        return link
    except Exception as e:
        session.rollback()
        return e
    finally:
        session.close()


def delete_link(link_id):
    session = SessionLocal()
    try:
        link = session.get(NetworkLink, link_id)
        if not link:
            return False
        session.delete(link)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        return e
    finally:
        session.close()


def get_links_by_ip(ip):
    session = SessionLocal()
    try:
        links = session.query(NetworkLink).options(
            selectinload(NetworkLink.source_device),
            selectinload(NetworkLink.destination_device)
        ).filter(
            (NetworkLink.source_ip == ip) | (NetworkLink.destination_ip == ip)
        ).all()
        return [
            {
                "id": link.id,
                "source_ip": link.source_ip,
                "destination_ip": link.destination_ip,
                "status": link.status,
                "remark": link.remark,
                "source_device_name": link.source_device.device_name if link.source_device else "",
                "destination_device_name": link.destination_device.device_name if link.destination_device else ""
            }
            for link in links
        ]
    finally:
        session.close()


# --- Cache helpers ---

def cache_topology(key, data):
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
    session = SessionLocal()
    try:
        session.query(TopologyCache).filter(TopologyCache.key.like(f"{key_prefix}%")).delete()
        session.commit()
        print(f"[DB] invalidate_cache({key_prefix}) -> invalidated")
    finally:
        session.close()

def category_list():
    session = SessionLocal()
    try:
        return [c.name.lower() for c in session.query(Category).all()]
    finally:
        session.close()
    
def category_add(cat):
    session = SessionLocal()
    try:
        if not cat or not cat.strip():
            return False, "Category name cannot be empty"

        category = Category(name=cat.strip())
        session.add(category)
        session.commit()

        return True, "Category added successfully"

    except IntegrityError:
        session.rollback()
        return False, "Category already exists"

    except Exception as e:
        session.rollback()
        return False, str(e)

    finally:
        session.close()


def get_dashboard_state(user_id=None):
    session = SessionLocal()
    try:
        state = session.query(DashboardState).first()
        if not state:
            return {"zoom": 1.0, "pan_x": 0.0, "pan_y": 0.0, "collapsed": [], "node_positions": {}, "layout_locked": False}
        return {
            "zoom": state.zoom,
            "pan_x": state.pan_x,
            "pan_y": state.pan_y,
            "collapsed": json.loads(state.collapsed),
            "node_positions": json.loads(state.node_positions),
            "layout_locked": state.layout_locked,
        }
    finally:
        session.close()


def save_dashboard_state(zoom=1.0, pan_x=0.0, pan_y=0.0, collapsed=None, node_positions=None, layout_locked=False, user_id=None):
    session = SessionLocal()
    try:
        state = session.query(DashboardState).first()
        collapsed_json = json.dumps(collapsed or [])
        positions_json = json.dumps(node_positions or {})
        if state:
            state.zoom = zoom
            state.pan_x = pan_x
            state.pan_y = pan_y
            state.collapsed = collapsed_json
            state.node_positions = positions_json
            state.layout_locked = layout_locked
        else:
            state = DashboardState(
                zoom=zoom,
                pan_x=pan_x,
                pan_y=pan_y,
                collapsed=collapsed_json,
                node_positions=positions_json,
                layout_locked=layout_locked,
            )
            session.add(state)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        return e
    finally:
        session.close()


def create_user(username, password, must_change_password=False):
    session = SessionLocal()
    try:
        if session.query(User).filter_by(user=username).first():
            return False, "Username already exists"
        user = User(
            user=username,
            passwd=generate_password_hash(password),
            must_change_password=must_change_password
        )
        session.add(user)
        session.commit()
        return True, "User created successfully"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_all_users():
    session = SessionLocal()
    try:
        users = session.query(User).all()
        return [{"id": u.id, "user": u.user, "must_change_password": u.must_change_password} for u in users]
    finally:
        session.close()


def delete_user(user_id):
    session = SessionLocal()
    try:
        user = session.get(User, user_id)
        if not user:
            return False, "User not found"
        session.delete(user)
        session.commit()
        return True, "User deleted"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def reset_user_password(user_id, new_password):
    session = SessionLocal()
    try:
        user = session.get(User, user_id)
        if not user:
            return False, "User not found"
        user.passwd = generate_password_hash(new_password)
        user.must_change_password = True
        session.commit()
        return True, "Password reset"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()
