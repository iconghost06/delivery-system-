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

# Seed default admin if not present
def seed_admin():
    conn = get_db_conn()
    try:
        admin_exists = conn.execute("SELECT * FROM admins WHERE username = 'admin'").fetchone()
        if not admin_exists:
            hashed = auth.hash_password("aura123")
            conn.execute("INSERT INTO admins (username, hashed_password) VALUES (?, ?)", ("admin", hashed))
            conn.commit()
            print("Default admin created: admin / aura123")
    except Exception as e:
        print("Error seeding admin:", e)
    finally:
        conn.close()

seed_admin()

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
    return templates.TemplateResponse("client_login.html", {"request": request, "error": error})

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
    
    # Load comments
    comments_rows = conn.execute("SELECT * FROM comments WHERE gallery_id = ?", (gallery["id"],)).fetchall()
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
            "comments_by_photo": comments_by_photo
        }
    )

@app.post("/api/gallery/{secure_hash}/favorite")
async def toggle_favorite(
    secure_hash: str,
    photo_id: int = Form(...),
):
    conn = get_db_conn()
    gallery = conn.execute("SELECT * FROM galleries WHERE secure_hash = ?", (secure_hash,)).fetchone()
    if not gallery:
        conn.close()
        return {"error": "Gallery not found"}
        
    existing = conn.execute(
        "SELECT * FROM favorites WHERE gallery_id = ? AND photo_id = ?",
        (gallery["id"], photo_id)
    ).fetchone()
    
    if existing:
        conn.execute("DELETE FROM favorites WHERE id = ?", (existing["id"],))
        conn.commit()
        conn.close()
        return {"status": "removed"}
    else:
        conn.execute(
            "INSERT INTO favorites (gallery_id, photo_id) VALUES (?, ?)",
            (gallery["id"], photo_id)
        )
        conn.commit()
        conn.close()
        return {"status": "added"}

@app.post("/api/gallery/{secure_hash}/comment")
async def add_comment(
    secure_hash: str,
    photo_id: int = Form(...),
    author: str = Form("Client"),
    text: str = Form(...)
):
    conn = get_db_conn()
    gallery = conn.execute("SELECT * FROM galleries WHERE secure_hash = ?", (secure_hash,)).fetchone()
    if not gallery:
        conn.close()
        return {"error": "Gallery not found"}
        
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO comments (gallery_id, photo_id, author, text) VALUES (?, ?, ?, ?)",
        (gallery["id"], photo_id, author, text)
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
        "timestamp": ts.strftime("%Y-%m-%d %H:%M")
    }

@app.get("/gallery/{secure_hash}/download")
async def download_gallery_photos(
    secure_hash: str,
    download_type: str = "all" # "all" or "favorites"
):
    conn = get_db_conn()
    gallery_row = conn.execute("SELECT * FROM galleries WHERE secure_hash = ?", (secure_hash,)).fetchone()
    if not gallery_row:
        conn.close()
        return {"error": "Gallery not found"}
        
    gallery = dict(gallery_row)
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
    
    conn.close()
    
    return templates.TemplateResponse(
        "admin_dashboard.html", 
        {
            "request": request, 
            "admin": admin, 
            "galleries": galleries, 
            "inquiries": inquiries,
            "clients": clients
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

@app.post("/admin/galleries/new")
async def admin_create_gallery(
    title: str = Form(...),
    description: str = Form(None),
    event_date: str = Form(None),
    is_private: bool = Form(False),
    client_id: int = Form(None),
    admin: dict = Depends(get_current_admin)
):
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        
    secure_hash = str(uuid.uuid4().hex[:12])
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO galleries (title, description, event_date, is_private, client_id, secure_hash) VALUES (?, ?, ?, ?, ?, ?)",
        (title, description, event_date, 1 if is_private else 0, client_id, secure_hash)
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
