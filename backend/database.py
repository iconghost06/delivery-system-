import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "photography.db")

def get_db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_conn()
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        hashed_password TEXT NOT NULL
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        hashed_password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS galleries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        secure_hash TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        event_date TEXT,
        cover_image TEXT,
        is_private INTEGER DEFAULT 0,
        password TEXT,
        client_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE SET NULL
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        original_name TEXT NOT NULL,
        upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        gallery_id INTEGER,
        FOREIGN KEY(gallery_id) REFERENCES galleries(id) ON DELETE CASCADE
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        gallery_id INTEGER,
        photo_id INTEGER,
        FOREIGN KEY(gallery_id) REFERENCES galleries(id) ON DELETE CASCADE,
        FOREIGN KEY(photo_id) REFERENCES photos(id) ON DELETE CASCADE
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        gallery_id INTEGER,
        photo_id INTEGER,
        author TEXT DEFAULT 'Client',
        text TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(gallery_id) REFERENCES galleries(id) ON DELETE CASCADE,
        FOREIGN KEY(photo_id) REFERENCES photos(id) ON DELETE CASCADE
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inquiries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT NOT NULL,
        event_type TEXT,
        event_date TEXT,
        message TEXT NOT NULL,
        status TEXT DEFAULT 'New',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quotes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        secure_hash TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        client_id INTEGER,
        inquiry_id INTEGER,
        status TEXT DEFAULT 'Draft',
        total_amount REAL DEFAULT 0.0,
        client_feedback TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE SET NULL,
        FOREIGN KEY(inquiry_id) REFERENCES inquiries(id) ON DELETE SET NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quote_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quote_id INTEGER NOT NULL,
        item_name TEXT NOT NULL,
        item_description TEXT,
        price REAL NOT NULL,
        quantity INTEGER DEFAULT 1,
        FOREIGN KEY(quote_id) REFERENCES quotes(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS calendar_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        start_date TEXT NOT NULL,
        end_date TEXT,
        client_id INTEGER,
        event_type TEXT DEFAULT 'Shoot',
        location TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE SET NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT UNIQUE NOT NULL,
        secure_hash TEXT UNIQUE NOT NULL,
        client_id INTEGER,
        quote_id INTEGER,
        title TEXT NOT NULL,
        issue_date TEXT NOT NULL,
        due_date TEXT NOT NULL,
        status TEXT DEFAULT 'Unpaid',
        subtotal REAL DEFAULT 0.0,
        discount REAL DEFAULT 0.0,
        tax_rate REAL DEFAULT 0.0,
        tax_amount REAL DEFAULT 0.0,
        total_amount REAL DEFAULT 0.0,
        billing_address TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE SET NULL,
        FOREIGN KEY(quote_id) REFERENCES quotes(id) ON DELETE SET NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoice_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER NOT NULL,
        item_name TEXT NOT NULL,
        item_description TEXT,
        price REAL NOT NULL,
        quantity INTEGER DEFAULT 1,
        FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
    );
    """)
    
    # Safe schema migrations for existing databases
    try:
        cursor.execute("ALTER TABLE galleries ADD COLUMN download_pin TEXT;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE galleries ADD COLUMN enable_watermark INTEGER DEFAULT 1;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE favorites ADD COLUMN author TEXT DEFAULT 'Client';")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE comments ADD COLUMN parent_id INTEGER;")
    except sqlite3.OperationalError:
        pass
    
    conn.commit()
    conn.close()

# Initialize DB on import
init_db()
