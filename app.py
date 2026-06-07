import os
from dotenv import load_dotenv
load_dotenv()

from db.models import *
from monitor.monitor import check_device
from db.database import SessionLocal, login,location_data,site_data,get_all_sites,get_all_locations,add_device,add_devices_bulk,full_topology,location_topology,location_sites,site_devices,add_location,add_site,save_topology_position,auto_place_site,update_location,delete_location,update_site,delete_site,get_all_devices,update_device,delete_device,get_details_paginated,device_status
from flask import Flask,request, redirect, flash, render_template, session, jsonify, Response
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from extensions import socketio
from monitor.scheduler import scheduler
from werkzeug.security import generate_password_hash
from captcha.image import ImageCaptcha
import random
import string
import io

def generate_captcha(length=6):
    return ''.join(
        random.choices(
            string.ascii_uppercase + string.digits,
            k=length
        )
    )

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change_this_to_random_secret")
socketio.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "/"

@login_manager.user_loader
def load_user(user_id):
    s = SessionLocal()
    try:
        return s.get(User, int(user_id))
    finally:
        s.close()

def create_default_admin():
    s = SessionLocal()
    try:
        if not s.query(User).first():
            admin_user = os.getenv("DEFAULT_ADMIN_USER", "admin")
            admin_pass = os.getenv("DEFAULT_ADMIN_PASS", "admin")
            admin = User(
                user=admin_user,
                passwd=generate_password_hash(admin_pass),
                must_change_password=False
            )
            s.add(admin)
            s.commit()
            print(f"Default admin user created ({admin_user}/{admin_pass})")
    finally:
        s.close()

@app.route("/captcha-image")
def captcha_image():
    text = session.get("captcha", "ABCD")
    image = ImageCaptcha(width=200, height=60)
    buf = io.BytesIO()
    image.write(text, buf)
    buf.seek(0)
    return Response(buf.getvalue(), mimetype="image/png")

@app.route("/", methods=["GET","POST"])
def index():
    if request.method =="POST":
        user= request.form.get("user")
        passwd= request.form.get("passwd")
        captcha= request.form.get("captcha")
        if captcha != session.get("captcha"):
            flash("Invalid Captcha")
            return redirect("/")
        response=login(username=user,password=passwd)
        if response is False:
            flash("Invalid Credentials")
        elif isinstance(response, Exception):
            flash(f"Error: {response}")
        else:
            login_user(response)
            if response.must_change_password:
                return redirect("/change-password")
            return redirect("/dashboard")
        return render_template("index.html")

    session["captcha"] = generate_captcha()
    return render_template("index.html")

@app.route("/change-password", methods=["GET","POST"])
@login_required
def change_password():
    if request.method=="POST":
        current_pw = request.form.get("current_password")
        new_pw = request.form.get("new_password")
        confirm_pw = request.form.get("confirm_password")
        from werkzeug.security import check_password_hash
        if not check_password_hash(current_user.passwd, current_pw):
            flash("Current password is incorrect")
            return redirect("/change-password")
        if new_pw != confirm_pw:
            flash("New passwords do not match")
            return redirect("/change-password")
        if len(new_pw) < 4:
            flash("Password must be at least 4 characters")
            return redirect("/change-password")
        s = SessionLocal()
        try:
            user = s.get(User, current_user.id)
            user.passwd = generate_password_hash(new_pw)
            user.must_change_password = False
            s.commit()
            flash("Password changed successfully")
        except Exception as e:
            s.rollback()
            flash(f"Error: {e}")
        finally:
            s.close()
        return redirect("/dashboard")
    return render_template("change_password.html")

@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.must_change_password:
        return redirect("/change-password")
    return render_template("radio.html")

@app.route("/dashboard/radio",methods=['GET','POST'])
@login_required
def radio():
    if current_user.must_change_password:
        return redirect("/change-password")
    if request.method=="GET":
        return render_template("radio.html")
    if request.method=="POST":
        location_id=request.form.get("location_id")
        site_id=request.form.get("site_id")
        if site_id == None:
            return redirect(f"/details/{location_id}")
        return redirect(f"/details/{location_id}/{site_id}")

@app.route("/details/<int:location_id>")
@login_required
def location_detail(location_id):
    if current_user.must_change_password:
        return redirect("/change-password")
    return render_template('details.html',show='location',detail=location_data(location_id))

@app.route("/details/<int:location_id>/<int:site_id>")
@login_required
def site_details(location_id,site_id):
    if current_user.must_change_password:
        return redirect("/change-password")
    return render_template('details.html',show='site',detail=site_data(site_id))

@app.route("/locations", methods=["GET","POST"])
@login_required
def locations_route():
    if current_user.must_change_password:
        return redirect("/change-password")
    if request.method=="POST":
        name=request.form.get("name")
        loc_id=request.form.get("id")
        if not name:
            flash("Location name is required")
            return redirect("/locations")
        if loc_id:
            result=update_location(int(loc_id), name.strip())
            if isinstance(result, Exception):
                flash(f"Error: {result}")
            else:
                flash("Location updated")
        else:
            result=add_location(name.strip())
            if result is False:
                flash("Location already exists")
            elif isinstance(result, Exception):
                flash(f"Error: {result}")
            else:
                flash(f"Location '{name}' added")
        return redirect("/locations")
    locations=get_all_locations()
    return render_template("locations.html", locations=locations, edit=None)

@app.route("/locations/edit/<int:loc_id>")
@login_required
def location_edit(loc_id):
    if current_user.must_change_password:
        return redirect("/change-password")
    locations=get_all_locations()
    edit=next((l for l in locations if l.id==loc_id), None)
    return render_template("locations.html", locations=locations, edit=edit)

@app.route("/locations/delete/<int:loc_id>")
@login_required
def location_delete(loc_id):
    if current_user.must_change_password:
        return redirect("/change-password")
    result=delete_location(loc_id)
    if isinstance(result, Exception):
        flash(f"Error: {result}")
    else:
        flash("Location deleted")
    return redirect("/locations")

@app.route("/sites", methods=["GET","POST"])
@login_required
def sites_route():
    if current_user.must_change_password:
        return redirect("/change-password")
    if request.method=="POST":
        name=request.form.get("name")
        location_id=request.form.get("location_id")
        site_id=request.form.get("id")
        if not name or not location_id:
            flash("All fields are required")
            return redirect("/sites")
        if site_id:
            result=update_site(int(site_id), name.strip(), int(location_id))
            if isinstance(result, Exception):
                flash(f"Error: {result}")
            else:
                flash("Site updated")
        else:
            result=add_site(name.strip(), int(location_id))
            if result is False:
                flash("Site already exists in this location")
            elif isinstance(result, Exception):
                flash(f"Error: {result}")
            else:
                auto_place_site(result.id)
                flash(f"Site '{name}' added")
        return redirect("/sites")
    sites=get_all_sites()
    locations=get_all_locations()
    return render_template("sites.html", sites=sites, locations=locations, edit=None)

@app.route("/sites/edit/<int:site_id>")
@login_required
def site_edit(site_id):
    if current_user.must_change_password:
        return redirect("/change-password")
    sites=get_all_sites()
    locations=get_all_locations()
    edit=next((s for s in sites if s.id==site_id), None)
    return render_template("sites.html", sites=sites, locations=locations, edit=edit)

@app.route("/sites/delete/<int:site_id>")
@login_required
def site_delete(site_id):
    if current_user.must_change_password:
        return redirect("/change-password")
    result=delete_site(site_id)
    if isinstance(result, Exception):
        flash(f"Error: {result}")
    else:
        flash("Site deleted")
    return redirect("/sites")

@app.route("/devices", methods=["GET","POST"])
@login_required
def devices_route():
    if current_user.must_change_password:
        return redirect("/change-password")
    edit_id=request.args.get("edit")
    if request.method=="POST":
        device_id=request.form.get("id")
        hostname=request.form.get("hostname")
        ip=request.form.get("ip")
        model=request.form.get("model")
        category=request.form.get("category")
        site_id=request.form.get("site_id")
        if not all([hostname, ip, model, category, site_id]):
            flash("All fields are required")
            return redirect("/devices")
        if device_id:
            result=update_device(int(device_id), hostname, ip, model, category, int(site_id))
            if isinstance(result, Exception):
                flash(f"Error: {result}")
            else:
                flash("Device updated")
        else:
            result=add_device(hostname=hostname, ip=ip, model=model, category=category, site_id=int(site_id))
            if isinstance(result, Exception):
                flash(f"Error: {result}")
            else:
                flash(f"Device {hostname} added")
        return redirect("/devices")
    devices=get_all_devices()
    sites=get_all_sites()
    edit=None
    if edit_id:
        edit=next((d for d in devices if str(d.id)==edit_id), None)
    return render_template("devices.html", devices=devices, sites=sites, edit=edit)

@app.route("/devices/delete/<int:device_id>")
@login_required
def device_delete(device_id):
    if current_user.must_change_password:
        return redirect("/change-password")
    result=delete_device(device_id)
    if isinstance(result, Exception):
        flash(f"Error: {result}")
    else:
        flash("Device deleted")
    return redirect("/devices")

@app.route("/devices/upload", methods=["GET","POST"])
@login_required
def upload_devices():
    if current_user.must_change_password:
        return redirect("/change-password")
    if request.method=="POST":
        file=request.files.get("file")
        if not file or file.filename=="":
            flash("No file selected")
            return redirect("/devices/upload")
        try:
            import openpyxl
            wb=openpyxl.load_workbook(file)
            ws=wb.active
            device_categories=["radio","ap","switch","router","server","other"]
            devices_data=[]
            for row in ws.iter_rows(min_row=2, values_only=True):
                hostname, ip, model, category, site_name = row[:5]
                if not hostname or not ip:
                    continue
                s = SessionLocal()
                try:
                    site = s.query(Site).filter(Site.name == site_name).first()
                finally:
                    s.close()
                if not site:
                    flash(f"Site '{site_name}' not found, skipping {hostname}")
                    continue
                cat=str(category).strip().lower() if category else "other"
                if cat not in device_categories:
                    cat="other"
                devices_data.append({
                    "hostname": str(hostname).strip(),
                    "ip": str(ip).strip(),
                    "model": str(model).strip() if model else "",
                    "category": cat,
                    "site_id": site.id
                })
            if devices_data:
                added, errors = add_devices_bulk(devices_data)
                flash(f"Added {len(added)} devices")
                for e in errors:
                    flash(f"Error: {e}")
            else:
                flash("No valid devices found in file")
        except Exception as e:
            flash(f"Error processing file: {e}")
        return redirect("/devices/upload")
    return render_template("upload_devices.html")

@app.route("/details/view")
@login_required
def details_view():
    if current_user.must_change_password:
        return redirect("/change-password")
    page=request.args.get("page", 1, type=int)
    per_page=request.args.get("per_page", 20, type=int)
    rows, total = get_details_paginated(page, per_page)
    total_pages=max(1, (total+per_page-1)//per_page)
    return render_template("details_view.html", rows=rows, page=page, total_pages=total_pages, total=total)

@app.route("/api/alerts")
def alerts_api():
    all_downs=[]
    for cat in ["radio","ap","switch","router","server","other"]:
        devs=device_status(cat) or []
        for d in devs:
            if d["status"] == False:
                all_downs.append(d)
    return jsonify(all_downs)

@app.route("/api/devices-list")
def devices_list_api():
    all_devices=[]
    for cat in ["radio","ap","switch","router","server","other"]:
        devs=device_status(cat)
        if devs:
            all_devices.extend(devs)
    return jsonify(all_devices)

@app.route("/api/devices-stats")
def api_devices_stats():
    s=SessionLocal()
    try:
        cats=["radio","ap","switch","router","server","other"]
        stats=[]
        total=0
        total_up=0
        for c in cats:
            cnt=s.query(Device).filter(Device.category==c).count()
            up=s.query(Device).filter(Device.category==c, Device.status==True).count()
            down=cnt-up
            total+=cnt
            total_up+=up
            stats.append({"category":c,"total":cnt,"up":up,"down":down})
        return jsonify({"categories":stats,"total":total,"up":total_up,"down":total-total_up})
    finally:
        s.close()

@app.route("/api/topology")
def topology_api():
    return jsonify(full_topology())

@app.route("/api/topology/locations")
def topology_locations_api():
    return jsonify(location_topology())

@app.route("/api/topology/location/<int:location_id>/sites")
def topology_location_sites_api(location_id):
    return jsonify(location_sites(location_id))

@app.route("/api/topology/site/<int:site_id>/devices")
def topology_site_devices_api(site_id):
    return jsonify(site_devices(site_id))

@app.route("/api/save-position", methods=["POST"])
@login_required
def save_position():
    data=request.get_json()
    site_id_str=data.get("site_id","").replace("site-","")
    try:
        site_id=int(site_id_str)
    except (ValueError, TypeError):
        return jsonify({"error": "invalid site_id"}), 400
    x=data.get("x")
    y=data.get("y")
    if x is None or y is None:
        return jsonify({"error": "x and y required"}), 400
    result=save_topology_position(site_id, x, y)
    if isinstance(result, Exception):
        return jsonify({"error": str(result)}), 500
    return jsonify({"ok": True})

@app.route("/api/save-positions", methods=["POST"])
@login_required
def save_positions():
    data=request.get_json()
    if not isinstance(data, list):
        return jsonify({"error": "expected a list of positions"}), 400
    errors=[]
    for item in data:
        site_id_str=str(item.get("site_id","")).replace("site-","")
        try:
            site_id=int(site_id_str)
        except (ValueError, TypeError):
            errors.append(f"invalid site_id: {item.get('site_id')}")
            continue
        x=item.get("x")
        y=item.get("y")
        if x is None or y is None:
            errors.append(f"missing x/y for site {site_id}")
            continue
        result=save_topology_position(site_id, x, y)
        if isinstance(result, Exception):
            errors.append(str(result))
    if errors:
        return jsonify({"ok": False, "errors": errors}), 207
    return jsonify({"ok": True, "saved": len(data)})

@app.route("/location/<int:location_id>")
@login_required
def location_page(location_id):
    s = SessionLocal()
    try:
        loc = s.query(Location).filter(Location.id == location_id).first()
        if not loc:
            return "Location not found", 404
        sites = s.query(Site).options(selectinload(Site.devices)).filter(Site.location_id == location_id).all()
        total_devices = sum(len(site.devices) for site in sites)
        down_devices = sum(sum(1 for d in site.devices if not d.status) for site in sites)
        site_data_list = []
        for site in sites:
            site_total = len(site.devices)
            site_down = sum(1 for d in site.devices if not d.status)
            site_data_list.append({
                "id": site.id,
                "name": site.name,
                "device_count": site_total,
                "down_count": site_down,
                "status": "GREEN" if site_down == 0 else ("RED" if site_down == site_total else "YELLOW")
            })
        return render_template("location.html",
            location=loc,
            sites=site_data_list,
            total_devices=total_devices,
            down_devices=down_devices
        )
    finally:
        s.close()

@app.route("/site/<int:site_id>")
@login_required
def site_page(site_id):
    s = SessionLocal()
    try:
        site = s.query(Site).options(selectinload(Site.location), selectinload(Site.devices)).filter(Site.id == site_id).first()
        if not site:
            return "Site not found", 404
        total_devices = len(site.devices)
        up_devices = sum(1 for d in site.devices if d.status)
        down_devices = total_devices - up_devices
        # Links for this site
        links = s.query(Link).options(
            selectinload(Link.source),
            selectinload(Link.destination),
            selectinload(Link.device_a_ref),
            selectinload(Link.device_b_ref)
        ).filter(
            (Link.source_site == site_id) | (Link.destination_site == site_id)
        ).all()
        link_data = []
        for link in links:
            other = link.destination if link.source_site == site_id else link.source
            other_id = link.destination_site if link.source_site == site_id else link.source_site
            link_data.append({
                "id": link.id,
                "other_site_name": other.name if other else "",
                "other_site_id": other_id,
                "device_a": link.device_a_ref.hostname if link.device_a_ref else "",
                "device_b": link.device_b_ref.hostname if link.device_b_ref else "",
                "status": link.status
            })
        # Paginated devices with search
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 25, type=int)
        search = request.args.get("search", "").strip()
        category_filter = request.args.get("category", "").strip()
        if per_page not in [25, 50, 100]:
            per_page = 25

        q = s.query(Device).filter(Device.site_id == site_id)
        if search:
            q = q.filter(Device.hostname.ilike(f"%{search}%"))
        if category_filter:
            q = q.filter(Device.category == category_filter)

        total_matching = q.count()
        total_pages = max(1, (total_matching + per_page - 1) // per_page)
        offset = (page - 1) * per_page
        devices = q.order_by(Device.hostname).offset(offset).limit(per_page).all()
        device_data = []
        for d in devices:
            device_data.append({
                "hostname": d.hostname,
                "ip": d.ip,
                "model": d.model,
                "category": d.category,
                "status": d.status
            })

        # All categories for filter dropdown
        categories = [r[0] for r in s.query(Device.category).filter(Device.site_id == site_id).distinct().all()]
        return render_template("site.html",
            site=site,
            total_devices=total_devices,
            up_devices=up_devices,
            down_devices=down_devices,
            total_matching=total_matching,
            links=link_data,
            devices=device_data,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            search=search,
            category_filter=category_filter,
            categories=categories
        )
    finally:
        s.close()

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")

if __name__ == "__main__":

    scheduler.start()
    Base.metadata.create_all(engine)
    create_default_admin()
    print("Database tables created.")
    debug_mode = os.getenv("DEBUG", "true").lower() == "true"
    socketio.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "5000")),
        debug=debug_mode,
        allow_unsafe_werkzeug=debug_mode
    )
