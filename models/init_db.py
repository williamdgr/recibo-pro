from database.connection import get_connection


def _migrate_receipts_drop_include_pix_qr(cursor):
    cursor.execute("PRAGMA table_info(receipts)")
    columns = [column["name"] for column in cursor.fetchall()]

    if "include_pix_qr" not in columns:
        return

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS receipts_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            cpf_cnpj TEXT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_method TEXT NOT NULL,
            pix_key TEXT,
            logo_path TEXT,
            city TEXT,
            issuer_name TEXT,
            pdf_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        INSERT INTO receipts_new (
            id, client_name, cpf_cnpj, description, amount, payment_method,
            pix_key, logo_path, city, issuer_name, pdf_path, created_at
        )
        SELECT
            id, client_name, cpf_cnpj, description, amount, payment_method,
            pix_key, logo_path, city, issuer_name, pdf_path, created_at
        FROM receipts
        """
    )

    cursor.execute("DROP TABLE receipts")
    cursor.execute("ALTER TABLE receipts_new RENAME TO receipts")

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            cpf TEXT,
            phone TEXT,
            credit_limit REAL DEFAULT 0
        )
    """)

    cursor.execute("PRAGMA table_info(clients)")
    clients_columns = [column["name"] for column in cursor.fetchall()]
    if "cpf" not in clients_columns:
        cursor.execute("ALTER TABLE clients ADD COLUMN cpf TEXT")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            amount REAL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            amount REAL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            cpf_cnpj TEXT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_method TEXT NOT NULL,
            pix_key TEXT,
            logo_path TEXT,
            city TEXT,
            issuer_name TEXT,
            pdf_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    _migrate_receipts_drop_include_pix_qr(cursor)

    conn.commit()
    conn.close()
