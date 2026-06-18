import os
import uuid
import zipfile
from io import BytesIO
from fastapi import FastAPI, Depends, Request, Form, UploadFile, File, Cookie, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import shutil

from .database import get_db_conn, init_db
from . import auth

# Initialize DB on startup
init_db()

# Seed default database if not present (admin, client, gallery, photos)
def seed_database():
    conn = get_db_conn()
    try:
        # 1. Admin
        admin_exists = conn.execute("SELECT * FROM admins WHERE username = 'admin'").fetchone()
        if not admin_exists:
            hashed = auth.hash_password("aura123")
            conn.execute("INSERT INTO admins (username, hashed_password) VALUES (?, ?)", ("admin", hashed))
            conn.commit()
            print("Default admin created: admin / aura123")
            
        # 2. Client
        client_exists = conn.execute("SELECT * FROM clients WHERE username = 'sanjay'").fetchone()
        if not client_exists:
            hashed = auth.hash_password("sanjay123")
            conn.execute("INSERT INTO clients (username, hashed_password) VALUES (?, ?)", ("sanjay", hashed))
            conn.commit()
            client_exists = conn.execute("SELECT * FROM clients WHERE username = 'sanjay'").fetchone()
            print("Default client created: sanjay / sanjay123")
            
        client_id = client_exists["id"]
        
        # 3. Gallery
        gallery_exists = conn.execute("SELECT * FROM galleries WHERE secure_hash = 'sanjay_priya'").fetchone()
        if not gallery_exists:
            conn.execute(
                "INSERT INTO galleries (secure_hash, title, description, event_date, cover_image, is_private, client_id, download_pin, enable_watermark) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("sanjay_priya", "Sanjay & Priya's Eternal Harmony", "A classic fine-art cinematic celebration of eternal commitment.", 
                 "2026-05-18", "https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&q=80&w=1200",
                 0, client_id, "1234", 1)
            )
            conn.commit()
            gallery_exists = conn.execute("SELECT * FROM galleries WHERE secure_hash = 'sanjay_priya'").fetchone()
            print("Default gallery created: sanjay_priya (PIN: 1234)")
            
        gallery_id = gallery_exists["id"]
        
        # 4. Photos
        photos_count = conn.execute("SELECT COUNT(*) FROM photos WHERE gallery_id = ?", (gallery_id,)).fetchone()[0]
        if photos_count == 0:
            sample_pics = [
                ("https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&q=80&w=1200", "ceremony_exchange.jpg"),
                ("https://images.unsplash.com/photo-1511285560929-80b456fea0bc?auto=format&fit=crop&q=80&w=1200", "garden_walk.jpg"),
                ("https://images.unsplash.com/photo-1583939003579-730e3918a45a?auto=format&fit=crop&q=80&w=1200", "royal_indian_wedding.jpg"),
                ("https://images.unsplash.com/photo-1507504038482-76210214dae1?auto=format&fit=crop&q=80&w=1200", "sunset_glance.jpg"),
                ("https://images.unsplash.com/photo-1520854221256-174b1ec35836?auto=format&fit=crop&q=80&w=1200", "the_first_kiss.jpg"),
                ("https://images.unsplash.com/photo-1523438885200-e635ba2c371e?auto=format&fit=crop&q=80&w=1200", "rings_and_vows.jpg"),
                ("https://images.unsplash.com/photo-1519225495810-7512c696505a?auto=format&fit=crop&q=80&w=1200", "bridal_radiance.jpg"),
                ("https://images.unsplash.com/photo-1537655780520-1e392edd816a?auto=format&fit=crop&q=80&w=1200", "maternity_sunset.jpg"),
                ("https://images.unsplash.com/photo-1516627145497-ae6968895b74?auto=format&fit=crop&q=80&w=1200", "newborn_tenderness.jpg"),
                ("https://images.unsplash.com/photo-1484807352052-23338990c6c6?auto=format&fit=crop&q=80&w=1200", "family_picnic.jpg")
            ]
            for url, orig_name in sample_pics:
                conn.execute(
                    "INSERT INTO photos (filename, original_name, gallery_id) VALUES (?, ?, ?)",
                    (url, orig_name, gallery_id)
                )
            conn.commit()
            print(f"Seeded {len(sample_pics)} photos for sanjay_priya gallery.")
    except Exception as e:
        print("Error seeding database:", e)
    finally:
        conn.close()

seed_database()

app = FastAPI(title="Aura Photography - Studio Portal")

# Static assets and uploads
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# Templates
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Dependency to verify admin session
async def get_current_admin(admin_session: str | None = Cookie(None)) -> dict | None:
    if not admin_session:
        return None
    username = auth.verify_session_token(admin_session)
    if not username:
        return None
    conn = get_db_conn()
    admin = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
    conn.close()
    if admin:
        return dict(admin)
    return None

# Dependency to verify client session
async def get_current_client(client_session: str | None = Cookie(None)) -> dict | None:
    if not client_session:
        return None
    username = auth.verify_session_token(client_session)
    if not username:
        return None
    conn = get_db_conn()
    client = conn.execute("SELECT * FROM clients WHERE username = ?", (username,)).fetchone()
    conn.close()
    if client:
        return dict(client)
    return None

# ==========================================
# PUBLIC PAGES ROUTES
# ==========================================

@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    return templates.TemplateResponse("home.html", {"request": request, "active_page": "home"})

@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    return templates.TemplateResponse("about.html", {"request": request, "active_page": "about"})

@app.get("/portfolio", response_class=HTMLResponse)
async def portfolio_page(request: Request):
    return templates.TemplateResponse("portfolio.html", {"request": request, "active_page": "portfolio"})

@app.get("/our-services", response_class=HTMLResponse)
async def services_page(request: Request):
    return templates.TemplateResponse("services.html", {"request": request, "active_page": "services"})

@app.get("/wedding-film", response_class=HTMLResponse)
async def wedding_film_page(request: Request):
    return templates.TemplateResponse("wedding_film.html", {"request": request, "active_page": "wedding_film"})

@app.get("/live-stream", response_class=HTMLResponse)
async def live_stream_page(request: Request):
    return templates.TemplateResponse("live_stream.html", {"request": request, "active_page": "live_stream"})

@app.get("/blog", response_class=HTMLResponse)
async def blog_page(request: Request):
    return templates.TemplateResponse("blog.html", {"request": request, "active_page": "blog"})

@app.get("/careers", response_class=HTMLResponse)
async def careers_page(request: Request):
    return templates.TemplateResponse("careers.html", {"request": request, "active_page": "careers"})

@app.get("/contact-us", response_class=HTMLResponse)
async def contact_page(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request, "active_page": "contact"})

@app.post("/contact-us/inquiry")
async def submit_inquiry(
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    event_type: str = Form(None),
    event_date: str = Form(None),
    message: str = Form(...)
):
    conn = get_db_conn()
    conn.execute(
        "INSERT INTO inquiries (name, email, phone, event_type, event_date, message) VALUES (?, ?, ?, ?, ?, ?)",
        (name, email, phone, event_type, event_date, message)
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/contact-us?success=true", status_code=status.HTTP_303_SEE_OTHER)


# ==========================================
# CLIENT PORTAL AUTH & DASHBOARD ROUTES
# ==========================================

@app.get("/client/login", response_class=HTMLResponse)
async def client_login_page(request: Request, error: str | None = None):
    return templates.TemplateResponse("client_login.html", {"request": request, "error": error, "active_page": "login"})

@app.post("/client/login")
async def client_login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
):
    conn = get_db_conn()
    client = conn.execute("SELECT * FROM clients WHERE username = ?", (username,)).fetchone()
    conn.close()
    
    if not client or not auth.verify_password(password, client["hashed_password"]):
        return RedirectResponse(
            url="/client/login?error=Invalid+username+or+password", 
            status_code=status.HTTP_303_SEE_OTHER
        )
        
    # Generate signed token
    token = auth.create_session_token(username)
    response = RedirectResponse(url="/client/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="client_session", value=token, httponly=True, max_age=3600 * 12) # 12 hours
    return response

@app.get("/client/logout")
async def client_logout(response: Response):
    response = RedirectResponse(url="/client/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("client_session")
    return response

@app.get("/client/dashboard", response_class=HTMLResponse)
async def client_dashboard(
    request: Request,
    client: dict = Depends(get_current_client)
):
    if not client:
        return RedirectResponse(url="/client/login", status_code=status.HTTP_303_SEE_OTHER)
        
    conn = get_db_conn()
    galleries_rows = conn.execute(
        "SELECT * FROM galleries WHERE client_id = ? ORDER BY created_at DESC", 
        (client["id"],)
    ).fetchall()
    
    galleries = []
    for g_row in galleries_rows:
        g = dict(g_row)
        photos_count = conn.execute("SELECT COUNT(*) FROM photos WHERE gallery_id = ?", (g["id"],)).fetchone()[0]
        g["photos"] = [0] * photos_count
        galleries.append(g)
        
    conn.close()
    
    return templates.TemplateResponse(
        "client_dashboard.html", 
        {"request": request, "client": client, "galleries": galleries}
    )


# ==========================================
# CLIENT GALLERY VIEWER
# ==========================================

@app.get("/gallery/{secure_hash}", response_class=HTMLResponse)
async def client_gallery(
    secure_hash: str,
    request: Request,
    client: dict = Depends(get_current_client)
):
    conn = get_db_conn()
    gallery_row = conn.execute("SELECT * FROM galleries WHERE secure_hash = ?", (secure_hash,)).fetchone()
    if not gallery_row:
        conn.close()
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    
    gallery = dict(gallery_row)
    
    # Check if gallery is private and check client association
    if gallery["is_private"]:
        if not client or client["id"] != gallery["client_id"]:
            conn.close()
            return RedirectResponse(
                url=f"/client/login?error=Please+log+in+to+view+your+private+gallery", 
                status_code=status.HTTP_303_SEE_OTHER
            )
            
    # Load photos
    photos_rows = conn.execute("SELECT * FROM photos WHERE gallery_id = ?", (gallery["id"],)).fetchall()
    photos = [dict(p) for p in photos_rows]
    gallery["photos"] = photos
    
    # Load favorites list for proofing state management
    favorites_rows = conn.execute("SELECT * FROM favorites WHERE gallery_id = ?", (gallery["id"],)).fetchall()
    favorite_photo_ids = {f["photo_id"] for f in favorites_rows}
    
    # Map favorites by photo to support multi-user selections
    favorites_by_photo = {}
    for f in favorites_rows:
        favorites_by_photo.setdefault(f["photo_id"], []).append(f["author"])
    
    # Load comments
    comments_rows = conn.execute("SELECT * FROM comments WHERE gallery_id = ? ORDER BY timestamp ASC", (gallery["id"],)).fetchall()
    comments_by_photo = {}
    for c in comments_rows:
        comments_by_photo.setdefault(c["photo_id"], []).append(dict(c))
        
    conn.close()

    return templates.TemplateResponse(
        "client_gallery.html", 
        {
            "request": request, 
            "gallery": gallery, 
            "favorite_photo_ids": favorite_photo_ids,
            "favorites_by_photo": favorites_by_photo,
            "comments_by_photo": comments_by_photo
        }
    )

@app.post("/api/gallery/{secure_hash}/favorite")
async def toggle_favorite(
    secure_hash: str,
    photo_id: int = Form(...),
    author: str = Form("Client")
):
    conn = get_db_conn()
    gallery = conn.execute("SELECT * FROM galleries WHERE secure_hash = ?", (secure_hash,)).fetchone()
    if not gallery:
        conn.close()
        return {"error": "Gallery not found"}
        
    existing = conn.execute(
        "SELECT * FROM favorites WHERE gallery_id = ? AND photo_id = ? AND author = ?",
        (gallery["id"], photo_id, author)
    ).fetchone()
    
    if existing:
        conn.execute("DELETE FROM favorites WHERE id = ?", (existing["id"],))
        conn.commit()
        conn.close()
        return {"status": "removed"}
    else:
        conn.execute(
            "INSERT INTO favorites (gallery_id, photo_id, author) VALUES (?, ?, ?)",
            (gallery["id"], photo_id, author)
        )
        conn.commit()
        conn.close()
        return {"status": "added"}

@app.post("/api/gallery/{secure_hash}/comment")
async def add_comment(
    secure_hash: str,
    photo_id: int = Form(...),
    author: str = Form("Client"),
    text: str = Form(...),
    parent_id: int = Form(None)
):
    conn = get_db_conn()
    gallery = conn.execute("SELECT * FROM galleries WHERE secure_hash = ?", (secure_hash,)).fetchone()
    if not gallery:
        conn.close()
        return {"error": "Gallery not found"}
        
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO comments (gallery_id, photo_id, author, text, parent_id) VALUES (?, ?, ?, ?, ?)",
        (gallery["id"], photo_id, author, text, parent_id)
    )
    conn.commit()
    
    comment_id = cursor.lastrowid
    comment = conn.execute("SELECT * FROM comments WHERE id = ?", (comment_id,)).fetchone()
    conn.close()
    
    import datetime
    ts = datetime.datetime.strptime(comment["timestamp"], "%Y-%m-%d %H:%M:%S") if " " in comment["timestamp"] else datetime.datetime.utcnow()
    
    return {
        "status": "success",
        "comment_id": comment["id"],
        "author": comment["author"],
        "text": comment["text"],
        "parent_id": comment["parent_id"],
        "timestamp": ts.strftime("%Y-%m-%d %H:%M")
    }

@app.get("/gallery/{secure_hash}/download")
async def download_gallery_photos(
    secure_hash: str,
    download_type: str = "all", # "all" or "favorites"
    pin: str = None
):
    conn = get_db_conn()
    gallery_row = conn.execute("SELECT * FROM galleries WHERE secure_hash = ?", (secure_hash,)).fetchone()
    if not gallery_row:
        conn.close()
        return {"error": "Gallery not found"}
        
    gallery = dict(gallery_row)
    
    # Secure Download PIN Verification
    if gallery.get("download_pin") and gallery["download_pin"].strip():
        if not pin or pin.strip() != gallery["download_pin"].strip():
            conn.close()
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Invalid Download PIN. Please contact the studio for access.")

    photos_rows = conn.execute("SELECT * FROM photos WHERE gallery_id = ?", (gallery["id"],)).fetchall()
    photos = [dict(p) for p in photos_rows]
    
    if download_type == "favorites":
        favs = conn.execute("SELECT * FROM favorites WHERE gallery_id = ?", (gallery["id"],)).fetchall()
        photo_ids = {f["photo_id"] for f in favs}
        photos = [p for p in photos if p["id"] in photo_ids]
        
    conn.close()
        
    if not photos:
        return {"error": "No photos to download"}
        
    # Compile a Zip file in memory
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for photo in photos:
            if photo["filename"].startswith("http"):
                try:
                    import urllib.request
                    import ssl
                    # Disable SSL verification for sample photos downloaded locally
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
                    
                    req = urllib.request.Request(
                        photo["filename"], 
                        headers={'User-Agent': 'Mozilla/5.0'}
                    )
                    with urllib.request.urlopen(req, timeout=5, context=ssl_context) as response:
                        img_data = response.read()
                        zip_file.writestr(photo["original_name"], img_data)
                except Exception as e:
                    print(f"Error downloading image {photo['filename']} for zip: {e}")
            else:
                filepath = os.path.join(UPLOAD_DIR, str(gallery["id"]), photo["filename"])
                if os.path.exists(filepath):
                    zip_file.write(filepath, photo["original_name"])
                
    zip_buffer.seek(0)
    
    filename = f"{gallery['title'].replace(' ', '_')}_{download_type}.zip"
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ==========================================
# ADMIN DASHBOARD ROUTES
# ==========================================

@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request, error: str | None = None):
    return templates.TemplateResponse("admin_login.html", {"request": request, "error": error})

@app.post("/admin/login")
async def admin_login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
):
    conn = get_db_conn()
    admin = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
    conn.close()
    
    if not admin or not auth.verify_password(password, admin["hashed_password"]):
        return RedirectResponse(
            url="/admin/login?error=Invalid+username+or+password", 
            status_code=status.HTTP_303_SEE_OTHER
        )
        
    # Generate signed token
    token = auth.create_session_token(username)
    response = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="admin_session", value=token, httponly=True, max_age=3600 * 12) # 12 hours
    return response

@app.get("/admin/logout")
async def admin_logout(response: Response):
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("admin_session")
    return response

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    admin: dict = Depends(get_current_admin)
):
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        
    conn = get_db_conn()
    galleries_rows = conn.execute("SELECT * FROM galleries ORDER BY created_at DESC").fetchall()
    galleries = []
    for g_row in galleries_rows:
        g = dict(g_row)
        # Count photos
        photos_count = conn.execute("SELECT COUNT(*) FROM photos WHERE gallery_id = ?", (g["id"],)).fetchone()[0]
        g["photos"] = [0] * photos_count # Mock list length for templates compatibility
        galleries.append(g)
        
    inquiries_rows = conn.execute("SELECT * FROM inquiries ORDER BY created_at DESC").fetchall()
    inquiries = [dict(i) for i in inquiries_rows]
    
    # Get all client accounts for the dropdowns
    clients_rows = conn.execute("SELECT * FROM clients ORDER BY username ASC").fetchall()
    clients = [dict(c) for c in clients_rows]
    
    # Get upcoming events
    upcoming_events_rows = conn.execute("""
        SELECT calendar_events.*, clients.username AS client_username 
        FROM calendar_events 
        LEFT JOIN clients ON calendar_events.client_id = clients.id
        WHERE date(calendar_events.start_date) >= date('now')
        ORDER BY calendar_events.start_date ASC
        LIMIT 5
    """).fetchall()
    upcoming_events = [dict(e) for e in upcoming_events_rows]
    
    conn.close()
    
    return templates.TemplateResponse(
        "admin_dashboard.html", 
        {
            "request": request, 
            "admin": admin, 
            "galleries": galleries, 
            "inquiries": inquiries,
            "clients": clients,
            "upcoming_events": upcoming_events
        }
    )

@app.post("/admin/clients/new")
async def admin_create_client(
    username: str = Form(...),
    password: str = Form(...),
    admin: dict = Depends(get_current_admin)
):
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        
    conn = get_db_conn()
    try:
        hashed = auth.hash_password(password)
        conn.execute("INSERT INTO clients (username, hashed_password) VALUES (?, ?)", (username, hashed))
        conn.commit()
    except Exception as e:
        print("Error creating client:", e)
    finally:
        conn.close()
        
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/clients/{id}/delete")
async def admin_delete_client(
    id: int,
    admin: dict = Depends(get_current_admin)
):
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        
    conn = get_db_conn()
    conn.execute("DELETE FROM clients WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/galleries/new")
async def admin_create_gallery(
    title: str = Form(...),
    description: str = Form(None),
    event_date: str = Form(None),
    is_private: bool = Form(False),
    client_id: int = Form(None),
    download_pin: str = Form(None),
    enable_watermark: bool = Form(True),
    admin: dict = Depends(get_current_admin)
):
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        
    secure_hash = str(uuid.uuid4().hex[:12])
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO galleries (title, description, event_date, is_private, client_id, secure_hash, download_pin, enable_watermark) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (title, description, event_date, 1 if is_private else 0, client_id, secure_hash, download_pin, 1 if enable_watermark else 0)
    )
    conn.commit()
    gallery_id = cursor.lastrowid
    conn.close()
    
    # Create folder for images
    gallery_dir = os.path.join(UPLOAD_DIR, str(gallery_id))
    os.makedirs(gallery_dir, exist_ok=True)
    
    return RedirectResponse(
        url=f"/admin/galleries/{gallery_id}/view", 
        status_code=status.HTTP_303_SEE_OTHER
    )

@app.post("/admin/galleries/{id}/update-settings")
async def admin_update_gallery_settings(
    id: int,
    download_pin: str = Form(None),
    enable_watermark: bool = Form(False),
    admin: dict = Depends(get_current_admin)
):
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        
    conn = get_db_conn()
    conn.execute(
        "UPDATE galleries SET download_pin = ?, enable_watermark = ? WHERE id = ?",
        (download_pin, 1 if enable_watermark else 0, id)
    )
    conn.commit()
    conn.close()
    
    return RedirectResponse(url=f"/admin/galleries/{id}/view", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/galleries/{id}/assign-client")
async def admin_assign_client(
    id: int,
    client_id: int = Form(None),
    admin: dict = Depends(get_current_admin)
):
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        
    conn = get_db_conn()
    conn.execute("UPDATE galleries SET client_id = ? WHERE id = ?", (client_id, id))
    conn.commit()
    conn.close()
    
    return RedirectResponse(url=f"/admin/galleries/{id}/view", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/admin/galleries/{id}/view", response_class=HTMLResponse)
async def admin_view_gallery(
    id: int,
    request: Request,
    admin: dict = Depends(get_current_admin)
):
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        
    conn = get_db_conn()
    gallery_row = conn.execute("SELECT * FROM galleries WHERE id = ?", (id,)).fetchone()
    if not gallery_row:
        conn.close()
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
        
    gallery = dict(gallery_row)
    photos_rows = conn.execute("SELECT * FROM photos WHERE gallery_id = ?", (gallery["id"],)).fetchall()
    photos = [dict(p) for p in photos_rows]
    gallery["photos"] = photos
    
    # Get favorite selections
    favs = conn.execute("SELECT * FROM favorites WHERE gallery_id = ?", (gallery["id"],)).fetchall()
    favorite_photo_ids = {f["photo_id"] for f in favs}
    
    # Get comments
    comments_rows = conn.execute("SELECT * FROM comments WHERE gallery_id = ?", (gallery["id"],)).fetchall()
    comments = [dict(c) for c in comments_rows]
    
    # Get client list for association dropdown
    clients_rows = conn.execute("SELECT * FROM clients ORDER BY username ASC").fetchall()
    clients = [dict(c) for c in clients_rows]
    
    conn.close()
    
    return templates.TemplateResponse(
        "admin_gallery_view.html",
        {
            "request": request,
            "admin": admin,
            "gallery": gallery,
            "favorite_photo_ids": favorite_photo_ids,
            "comments": comments,
            "clients": clients
        }
    )

@app.post("/admin/galleries/{id}/upload")
async def admin_upload_photos(
    id: int,
    files: list[UploadFile] = File(...),
    admin: dict = Depends(get_current_admin)
):
    if not admin:
        return {"error": "Unauthorized"}
        
    conn = get_db_conn()
    gallery_row = conn.execute("SELECT * FROM galleries WHERE id = ?", (id,)).fetchone()
    if not gallery_row:
        conn.close()
        return {"error": "Gallery not found"}
        
    gallery = dict(gallery_row)
    gallery_dir = os.path.join(UPLOAD_DIR, str(gallery["id"]))
    os.makedirs(gallery_dir, exist_ok=True)
    
    uploaded_photos = []
    
    for file in files:
        if not file.filename:
            continue
            
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
            continue
            
        # Secure filename with UUID to avoid overwriting
        safe_filename = f"{uuid.uuid4().hex}{file_ext}"
        filepath = os.path.join(gallery_dir, safe_filename)
        
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Set cover image automatically if not set
        if not gallery.get("cover_image"):
            cover_path = f"/static/uploads/{gallery['id']}/{safe_filename}"
            conn.execute("UPDATE galleries SET cover_image = ? WHERE id = ?", (cover_path, gallery["id"]))
            conn.commit()
            gallery["cover_image"] = cover_path
            
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO photos (filename, original_name, gallery_id) VALUES (?, ?, ?)",
            (safe_filename, file.filename, gallery["id"])
        )
        conn.commit()
        photo_id = cursor.lastrowid
        
        uploaded_photos.append({
            "id": photo_id,
            "original_name": file.filename,
            "url": f"/static/uploads/{gallery['id']}/{safe_filename}"
        })
        
    conn.close()
    return {"status": "success", "uploaded": uploaded_photos}

@app.post("/admin/galleries/{id}/delete")
async def admin_delete_gallery(
    id: int,
    admin: dict = Depends(get_current_admin)
):
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        
    conn = get_db_conn()
    gallery = conn.execute("SELECT * FROM galleries WHERE id = ?", (id,)).fetchone()
    if gallery:
        # Delete directory
        gallery_dir = os.path.join(UPLOAD_DIR, str(gallery["id"]))
        if os.path.exists(gallery_dir):
            shutil.rmtree(gallery_dir)
            
        conn.execute("DELETE FROM galleries WHERE id = ?", (id,))
        conn.commit()
        
    conn.close()
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/inquiries/{id}/status")
async def admin_update_inquiry_status(
    id: int,
    status: str = Form(...),
    admin: dict = Depends(get_current_admin)
):
    if not admin:
        return {"error": "Unauthorized"}
        
    conn = get_db_conn()
    inquiry = conn.execute("SELECT * FROM inquiries WHERE id = ?", (id,)).fetchone()
    if inquiry:
        conn.execute("UPDATE inquiries SET status = ? WHERE id = ?", (status, id))
        conn.commit()
        conn.close()
        return {"status": "success"}
    conn.close()
    return {"error": "Inquiry not found"}


# ==========================================
# SAAS QUOTES & PROPOSALS ROUTES
# ==========================================

@app.get("/admin/quotes", response_class=HTMLResponse)
async def admin_quotes_list(
    request: Request,
    admin: dict = Depends(get_current_admin)
):
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        
    conn = get_db_conn()
    quotes_rows = conn.execute("""
        SELECT quotes.*, clients.username AS client_username, inquiries.name AS inquiry_name, inquiries.event_type AS inquiry_event
        FROM quotes
        LEFT JOIN clients ON quotes.client_id = clients.id
        LEFT JOIN inquiries ON quotes.inquiry_id = inquiries.id
        ORDER BY quotes.created_at DESC
    """).fetchall()
    quotes = [dict(q) for q in quotes_rows]
    
    clients_rows = conn.execute("SELECT * FROM clients ORDER BY username ASC").fetchall()
    clients = [dict(c) for c in clients_rows]
    
    inquiries_rows = conn.execute("SELECT * FROM inquiries ORDER BY created_at DESC").fetchall()
    inquiries = [dict(i) for i in inquiries_rows]
    conn.close()
    
    return templates.TemplateResponse(
        "admin_quotes.html",
        {
            "request": request,
            "admin": admin,
            "quotes": quotes,
            "clients": clients,
            "inquiries": inquiries
        }
    )

@app.post("/admin/quotes/new")
async def admin_create_quote(
    request: Request,
    admin: dict = Depends(get_current_admin)
):
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        
    form_data = await request.form()
    title = form_data.get("title")
    description = form_data.get("description")
    
    client_id_raw = form_data.get("client_id")
    client_id = int(client_id_raw) if client_id_raw else None
    
    inquiry_id_raw = form_data.get("inquiry_id")
    inquiry_id = int(inquiry_id_raw) if inquiry_id_raw else None
    
    secure_hash = uuid.uuid4().hex
    
    conn = get_db_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO quotes (secure_hash, title, description, client_id, inquiry_id) VALUES (?, ?, ?, ?, ?)",
            (secure_hash, title, description, client_id, inquiry_id)
        )
        quote_id = cursor.lastrowid
        
        # Extract line items list
        item_names = form_data.getlist("item_name[]")
        item_descs = form_data.getlist("item_desc[]")
        item_prices = form_data.getlist("item_price[]")
        item_qtys = form_data.getlist("item_qty[]")
        
        total_amount = 0.0
        for i in range(len(item_names)):
            name = item_names[i]
            desc = item_descs[i] if i < len(item_descs) else ""
            price = float(item_prices[i]) if i < len(item_prices) and item_prices[i] else 0.0
            qty = int(item_qtys[i]) if i < len(item_qtys) and item_qtys[i] else 1
            
            conn.execute(
                "INSERT INTO quote_items (quote_id, item_name, item_description, price, quantity) VALUES (?, ?, ?, ?, ?)",
                (quote_id, name, desc, price, qty)
            )
            total_amount += price * qty
            
        # Update total amount
        conn.execute("UPDATE quotes SET total_amount = ? WHERE id = ?", (total_amount, quote_id))
        conn.commit()
    finally:
        conn.close()
    
    return RedirectResponse(url="/admin/quotes", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/quotes/{id}/delete")
async def admin_delete_quote(
    id: int,
    admin: dict = Depends(get_current_admin)
):
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        
    conn = get_db_conn()
    conn.execute("DELETE FROM quotes WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/admin/quotes", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/quotes/{id}/send")
async def admin_send_quote(
    id: int,
    admin: dict = Depends(get_current_admin)
):
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        
    conn = get_db_conn()
    quote = conn.execute("SELECT * FROM quotes WHERE id = ?", (id,)).fetchone()
    if quote:
        conn.execute("UPDATE quotes SET status = 'Sent' WHERE id = ?", (id,))
        conn.commit()
        # Mock Email log
        print(f"[MOCK EMAIL] Proposal '{quote['title']}' sent to Client (ID: {quote['client_id'] or 'Direct'}). Access link: /quote/{quote['secure_hash']}")
    conn.close()
    return RedirectResponse(url="/admin/quotes", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/quote/{secure_hash}", response_class=HTMLResponse)
async def view_proposal(
    request: Request,
    secure_hash: str
):
    conn = get_db_conn()
    quote_row = conn.execute("SELECT * FROM quotes WHERE secure_hash = ?", (secure_hash,)).fetchone()
    if not quote_row:
        conn.close()
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
        
    quote = dict(quote_row)
    items_rows = conn.execute("SELECT * FROM quote_items WHERE quote_id = ?", (quote["id"],)).fetchall()
    items = [dict(it) for it in items_rows]
    conn.close()
    
    return templates.TemplateResponse(
        "client_quote.html",
        {
            "request": request,
            "quote": quote,
            "items": items
        }
    )

@app.post("/quote/{secure_hash}/approve")
async def approve_proposal(
    secure_hash: str
):
    conn = get_db_conn()
    quote = conn.execute("SELECT * FROM quotes WHERE secure_hash = ?", (secure_hash,)).fetchone()
    if quote:
        conn.execute("UPDATE quotes SET status = 'Approved' WHERE secure_hash = ?", (secure_hash,))
        conn.commit()
        # Mock Email notify
        print(f"[MOCK EMAIL] Proposal '{quote['title']}' was APPROVED by the Client!")
    conn.close()
    return RedirectResponse(url=f"/quote/{secure_hash}", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/quote/{secure_hash}/reject")
async def request_proposal_revision(
    secure_hash: str,
    feedback: str = Form(...)
):
    conn = get_db_conn()
    quote = conn.execute("SELECT * FROM quotes WHERE secure_hash = ?", (secure_hash,)).fetchone()
    if quote:
        conn.execute("UPDATE quotes SET status = 'Revised', client_feedback = ? WHERE secure_hash = ?", (feedback, secure_hash))
        conn.commit()
        # Mock Email notify
        print(f"[MOCK EMAIL] Client requested revision for '{quote['title']}'. Feedback: {feedback}")
    conn.close()
    return RedirectResponse(url=f"/quote/{secure_hash}", status_code=status.HTTP_303_SEE_OTHER)


# ==========================================
# SAAS EVENT CALENDAR ROUTES
# ==========================================

@app.get("/admin/calendar", response_class=HTMLResponse)
async def admin_calendar_view(
    request: Request,
    admin: dict = Depends(get_current_admin)
):
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        
    conn = get_db_conn()
    events_rows = conn.execute("""
        SELECT calendar_events.*, clients.username AS client_username 
        FROM calendar_events 
        LEFT JOIN clients ON calendar_events.client_id = clients.id
        ORDER BY calendar_events.start_date ASC
    """).fetchall()
    events = [dict(e) for e in events_rows]
    
    clients_rows = conn.execute("SELECT * FROM clients ORDER BY username ASC").fetchall()
    clients = [dict(c) for c in clients_rows]
    conn.close()
    
    return templates.TemplateResponse(
        "admin_calendar.html",
        {
            "request": request,
            "admin": admin,
            "events": events,
            "clients": clients
        }
    )

@app.post("/admin/calendar/events/new")
async def admin_create_calendar_event(
    title: str = Form(...),
    start_date: str = Form(...),
    event_type: str = Form("Shoot"),
    client_id: int | None = Form(None),
    location: str = Form(None),
    description: str = Form(None),
    admin: dict = Depends(get_current_admin)
):
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        
    conn = get_db_conn()
    conn.execute(
        "INSERT INTO calendar_events (title, start_date, event_type, client_id, location, description) VALUES (?, ?, ?, ?, ?, ?)",
        (title, start_date, event_type, client_id, location, description)
    )
    conn.commit()
    conn.close()
    
    return RedirectResponse(url="/admin/calendar", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/calendar/events/{id}/delete")
async def admin_delete_calendar_event(
    id: int,
    admin: dict = Depends(get_current_admin)
):
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        
    conn = get_db_conn()
    conn.execute("DELETE FROM calendar_events WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    
    return RedirectResponse(url="/admin/calendar", status_code=status.HTTP_303_SEE_OTHER)


# ==========================================
# SAAS INVOICES & BILLING ROUTES (ZOHO CLONE)
# ==========================================

@app.get("/admin/invoices", response_class=HTMLResponse)
async def admin_invoices_list(
    request: Request,
    admin: dict = Depends(get_current_admin)
):
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        
    conn = get_db_conn()
    invoices_rows = conn.execute("""
        SELECT invoices.*, clients.username AS client_username 
        FROM invoices
        LEFT JOIN clients ON invoices.client_id = clients.id
        ORDER BY invoices.created_at DESC
    """).fetchall()
    invoices = [dict(inv) for inv in invoices_rows]
    
    clients_rows = conn.execute("SELECT * FROM clients ORDER BY username ASC").fetchall()
    clients = [dict(c) for c in clients_rows]
    conn.close()
    
    return templates.TemplateResponse(
        "admin_invoices.html",
        {
            "request": request,
            "admin": admin,
            "invoices": invoices,
            "clients": clients
        }
    )

@app.post("/admin/invoices/new")
async def admin_create_invoice(
    request: Request,
    admin: dict = Depends(get_current_admin)
):
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        
    form_data = await request.form()
    invoice_number = form_data.get("invoice_number")
    title = form_data.get("title")
    billing_address = form_data.get("billing_address")
    notes = form_data.get("notes")
    issue_date = form_data.get("issue_date")
    due_date = form_data.get("due_date")
    
    client_id_raw = form_data.get("client_id")
    client_id = int(client_id_raw) if client_id_raw else None
    
    tax_rate = float(form_data.get("tax_rate", 0.0))
    discount = float(form_data.get("discount", 0.0))
    
    secure_hash = uuid.uuid4().hex
    
    conn = get_db_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO invoices (invoice_number, secure_hash, client_id, title, issue_date, due_date, tax_rate, discount, billing_address, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (invoice_number, secure_hash, client_id, title, issue_date, due_date, tax_rate, discount, billing_address, notes)
        )
        invoice_id = cursor.lastrowid
        
        # Line items
        item_names = form_data.getlist("item_name[]")
        item_descs = form_data.getlist("item_desc[]")
        item_prices = form_data.getlist("item_price[]")
        item_qtys = form_data.getlist("item_qty[]")
        
        subtotal = 0.0
        for i in range(len(item_names)):
            name = item_names[i]
            desc = item_descs[i] if i < len(item_descs) else ""
            price = float(item_prices[i]) if i < len(item_prices) and item_prices[i] else 0.0
            qty = int(item_qtys[i]) if i < len(item_qtys) and item_qtys[i] else 1
            
            conn.execute(
                "INSERT INTO invoice_items (invoice_id, item_name, item_description, price, quantity) VALUES (?, ?, ?, ?, ?)",
                (invoice_id, name, desc, price, qty)
            )
            subtotal += price * qty
            
        base_amount = max(0.0, subtotal - discount)
        tax_amount = base_amount * (tax_rate / 100.0)
        total_amount = base_amount + tax_amount
        
        conn.execute(
            "UPDATE invoices SET subtotal = ?, tax_amount = ?, total_amount = ? WHERE id = ?",
            (subtotal, tax_amount, total_amount, invoice_id)
        )
        conn.commit()
    finally:
        conn.close()
        
    return RedirectResponse(url="/admin/invoices", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/quotes/{id}/convert")
async def admin_convert_quote_to_invoice(
    id: int,
    admin: dict = Depends(get_current_admin)
):
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        
    conn = get_db_conn()
    try:
        quote = conn.execute("SELECT * FROM quotes WHERE id = ?", (id,)).fetchone()
        if not quote:
            conn.close()
            return RedirectResponse(url="/admin/quotes", status_code=status.HTTP_303_SEE_OTHER)
            
        items = conn.execute("SELECT * FROM quote_items WHERE quote_id = ?", (id,)).fetchall()
        
        # Build invoice variables
        import random
        from datetime import datetime, timedelta
        
        random_num = random.randint(1000, 9999)
        invoice_number = f"INV-{datetime.now().year}-{random_num}"
        secure_hash = uuid.uuid4().hex
        
        today = datetime.now()
        issue_date = today.strftime("%Y-%m-%d")
        due_date = (today + timedelta(days=15)).strftime("%Y-%m-%d")
        
        tax_rate = 18.0  # Standard GST percentage
        subtotal = quote["total_amount"]
        tax_amount = subtotal * 0.18
        total_amount = subtotal + tax_amount
        
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO invoices (invoice_number, secure_hash, client_id, quote_id, title, issue_date, due_date, status, subtotal, tax_rate, tax_amount, total_amount, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'Unpaid', ?, ?, ?, ?, ?)",
            (invoice_number, secure_hash, quote["client_id"], id, f"Invoice for {quote['title']}", issue_date, due_date, subtotal, tax_rate, tax_amount, total_amount, "Converted automatically from approved package quote.")
        )
        invoice_id = cursor.lastrowid
        
        # Copy line items
        for it in items:
            conn.execute(
                "INSERT INTO invoice_items (invoice_id, item_name, item_description, price, quantity) VALUES (?, ?, ?, ?, ?)",
                (invoice_id, it["item_name"], it["item_description"], it["price"], it["quantity"])
            )
            
        # Optional: update quote status/reference
        conn.commit()
    finally:
        conn.close()
        
    return RedirectResponse(url="/admin/invoices", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/invoices/{id}/pay")
async def admin_record_invoice_payment(
    id: int,
    admin: dict = Depends(get_current_admin)
):
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        
    conn = get_db_conn()
    conn.execute("UPDATE invoices SET status = 'Paid' WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/admin/invoices", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/invoices/{id}/delete")
async def admin_delete_invoice(
    id: int,
    admin: dict = Depends(get_current_admin)
):
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        
    conn = get_db_conn()
    conn.execute("DELETE FROM invoices WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/admin/invoices", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/invoice/{secure_hash}", response_class=HTMLResponse)
async def view_invoice_portal(
    request: Request,
    secure_hash: str
):
    conn = get_db_conn()
    inv_row = conn.execute("SELECT * FROM invoices WHERE secure_hash = ?", (secure_hash,)).fetchone()
    if not inv_row:
        conn.close()
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
        
    invoice = dict(inv_row)
    items_rows = conn.execute("SELECT * FROM invoice_items WHERE invoice_id = ?", (invoice["id"],)).fetchall()
    items = [dict(it) for it in items_rows]
    conn.close()
    
    return templates.TemplateResponse(
        "client_invoice.html",
        {
            "request": request,
            "invoice": invoice,
            "items": items
        }
    )
