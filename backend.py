import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import datetime

# Inisialisasi Koneksi ke 'connections.postgresql' di secrets.toml
conn = st.connection("postgresql", type="sql")

# ==============================================================================
# HELPER: EMAIL NOTIFICATION
# ==============================================================================

def send_email_notification(recipient_email, subject, body_html):
    """Mengirim email notifikasi menggunakan konfigurasi SMTP dari secrets.toml."""
    try:
        smtp_config = st.secrets.get("smtp", {})
        SMTP_SERVER = smtp_config.get("server")
        SMTP_PORT = int(smtp_config.get("port", 587))
        SENDER_EMAIL = smtp_config.get("email")
        SENDER_PASSWORD = smtp_config.get("password")
        
        if not all([SMTP_SERVER, SENDER_EMAIL, SENDER_PASSWORD]):
            return {"status": 500, "message": "Konfigurasi SMTP tidak lengkap di secrets.toml"}
    except Exception as e:
        return {"status": 500, "message": f"Gagal membaca secrets: {e}"}

    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body_html, 'html'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
        server.starttls() 
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        return {"status": 200, "message": "Email sent successfully"}
    except Exception as e:
        return {"status": 500, "message": f"SMTP Error: {str(e)}"}

# ==============================================================================
# 1. AUTHENTICATION & USER MANAGEMENT
# ==============================================================================

def validate_user(username, password):
    """Memvalidasi login user dari tabel 'users'."""
    query = "SELECT * FROM users WHERE sales_name = :u AND password = :p"
    df = conn.query(query, params={"u": username, "p": password}, ttl=0)
    
    if not df.empty:
        user_data = df.iloc[0]
        sales_group = user_data.get('salesgroup') or user_data.get('salesGroup') or user_data.get('sales_group')
        
        return {
            "status": 200, 
            "data": {
                "salesName": user_data['sales_name'], 
                "salesGroup": sales_group
            }
        }
    return {"status": 401, "message": "Nama atau Password salah."}

def get_sales_names():
    df = conn.query("SELECT sales_name FROM users ORDER BY sales_name", ttl=600)
    return df['sales_name'].tolist()

# ==============================================================================
# 2. READ DATA (GET) - KANBAN & SEARCH
# ==============================================================================

def get_kanban_data(sales_group, sales_name, is_super_user=False):
    """Mengambil data Kanban dengan bypass untuk TOP_MGMT."""
    base_query = """
        SELECT DISTINCT ON (opportunity_id)
            opportunity_id, 
            opportunity_name, 
            company_name,
            sales_name, 
            salesgroup_id,  
            stage, 
            selling_price, 
            sales_notes
        FROM opportunities
        WHERE 1=1
    """
    params = {}

    # LOGIKA BARU: Bypass filter jika TOP_MGMT
    if sales_group != 'TOP_MGMT':
        base_query += " AND salesgroup_id = :sg"
        params["sg"] = sales_group
        
        if not is_super_user:
            base_query += " AND sales_name = :sn"
            params["sn"] = sales_name
            
    base_query += " ORDER BY opportunity_id"
    
    df = conn.query(base_query, params=params, ttl=60)
    
    if not df.empty:
        df = df.drop_duplicates(subset=['opportunity_id'], keep='first')
        if 'selling_price' in df.columns:
            df['selling_price'] = pd.to_numeric(df['selling_price'], errors='coerce').fillna(0)
            
    return df

def get_dashboard_data(sales_group, sales_name, is_super_user=False):
    """Mengambil data detail untuk Dashboard dengan bypass TOP_MGMT."""
    query = "SELECT * FROM opportunities WHERE 1=1" 
    params = {}
    
    if sales_group != 'TOP_MGMT':
        query += " AND salesgroup_id = :sg"
        params["sg"] = sales_group
        
        if not is_super_user:
            query += " AND sales_name = :sn"
            params["sn"] = sales_name
    
    df = conn.query(query, params=params, ttl=300)
    return df

def get_opportunity_details(opportunity_id):
    """Mengambil detail item (produk/solusi) untuk satu opportunity."""
    query = """
        SELECT pillar, solution, service, brand, selling_price 
        FROM opportunities 
        WHERE opportunity_id = :oid
    """
    df = conn.query(query, params={"oid": opportunity_id}, ttl=60)
    return df

def search_opportunities(keyword, search_by, sales_group, sales_name, is_super_user=False):
    """Search dengan batasan otoritas dan bypass TOP_MGMT."""
    col_map = {
        "Opportunity Name": "opportunity_name",
        "Company": "company_name",
        "Sales Name": "sales_name",
        "Stage": "stage"
    }
    db_col = col_map.get(search_by, "opportunity_name")
    
    query = f"""
        SELECT DISTINCT ON (opportunity_id) 
            opportunity_id, opportunity_name, company_name, sales_name, stage, selling_price 
        FROM opportunities 
        WHERE {db_col} ILIKE :kw
    """
    params = {"kw": f"%{keyword}%"}
    
    if sales_group != 'TOP_MGMT':
        query += " AND salesgroup_id = :sg"
        params["sg"] = sales_group
        
        if not is_super_user:
            query += " AND sales_name = :sn"
            params["sn"] = sales_name
            
    query += " ORDER BY opportunity_id"
        
    df = conn.query(query, params=params, ttl=0)
    
    if not df.empty:
        df = df.drop_duplicates(subset=['opportunity_id'], keep='first')
        
    return df

# ==============================================================================
# 3. MASTER DATA DROPDOWNS
# ==============================================================================

def get_master_data(table_name, column_name):
    valid_tables = ["brands", "companies", "master_pillars", "distributors", "stage_pipeline"]
    if table_name not in valid_tables:
        return []
        
    query = f"SELECT {column_name} FROM {table_name} ORDER BY {column_name}"
    df = conn.query(query, ttl=3600) 
    return df[column_name].tolist()

# ==============================================================================
# 4. WRITE DATA (POST/UPDATE) - TRANSACTIONAL
# ==============================================================================

def run_transaction(query_text, params):
    """Helper untuk eksekusi Write dengan Commit/Rollback yang aman."""
    with conn.engine.connect() as connection:
        trans = connection.begin()
        try:
            connection.execute(text(query_text), params)
            trans.commit()
            return True, "Success"
        except Exception as e:
            trans.rollback()
            return False, str(e)

def log_sales_activity(opp_id, opp_name, user, action, field, old_val, new_val):
    """Mencatat log dengan Opportunity ID sebagai referensi utama."""
    try:
        query = """
            INSERT INTO activity_logs_sales 
            (timestamp, opportunity_id, opportunity_name, user_name, action, old_value, new_value)
            VALUES (NOW(), :oid, :on, :un, :act, :old, :new)
        """
        params = {
            "oid": opp_id, "on": opp_name, "un": user, 
            "act": f"{action} - {field}", # Info field digabung ke dalam nama action
            "old": str(old_val), "new": str(new_val)
        }
        run_transaction(query, params)
    except Exception as e:
        print(f"Log Error: {e}")

# ==============================================================================
# 5. LUMP SUM PRICE UPDATE (HEADER)
# ==============================================================================

def get_sales_opportunity_header(opp_id):
    """Mengambil data header dari opportunities (LIMIT 1)."""
    query = """
        SELECT 
            opportunity_id, opportunity_name, company_name, 
            sales_name, presales_name, stage, selling_price, sales_notes
        FROM opportunities
        WHERE opportunity_id = :oid
        LIMIT 1
    """
    df = conn.query(query, params={"oid": opp_id}, ttl=0)
    if not df.empty:
        return df.iloc[0].to_dict()
    return None

def update_lump_sum_price_header(opp_id, new_price, user_name):
    """Update harga total (Lump Sum) di seluruh baris opportunity terkait."""
    try:
        with conn.engine.connect() as connection:
            trans = connection.begin()
            try:
                old_data = connection.execute(
                    text("SELECT selling_price, opportunity_name FROM opportunities WHERE opportunity_id = :oid LIMIT 1"),
                    {"oid": opp_id}
                ).mappings().first()

                old_val = old_data['selling_price'] if old_data and old_data['selling_price'] else 0
                opp_name = old_data['opportunity_name'] if old_data else "Unknown"

                upd_q = text("""
                    UPDATE opportunities 
                    SET selling_price = :price, updated_at = NOW() 
                    WHERE opportunity_id = :oid
                """)
                connection.execute(upd_q, {"price": new_price, "oid": opp_id})

                if float(old_val) != float(new_price):
                    log_sales_activity(opp_id, opp_name, user_name, "UPDATE PRICE", "Lump Sum Selling Price", str(old_val), str(new_price))

                trans.commit()
                return {"status": 200, "message": f"Harga berhasil diupdate menjadi Rp {new_price:,.0f}"}
            except Exception as e:
                trans.rollback()
                return {"status": 500, "message": str(e)}
    except Exception as e:
        return {"status": 500, "message": str(e)}

def get_opportunity_line_items(opp_id):
    """Mengambil detail item beserta UID dan harga saat ini."""
    query = """
        SELECT 
            uid, product_id, pillar, solution, brand, service, cost, selling_price
        FROM opportunities 
        WHERE opportunity_id = :oid
        ORDER BY created_at
    """
    return conn.query(query, params={"oid": opp_id}, ttl=0)

def update_line_item_prices(updates_list, user_name, opp_id, opp_name):
    """
    Update selling_price HANYA pada baris yang diubah oleh Sales, 
    berdasarkan 'uid' masing-masing item.
    """
    try:
        with conn.engine.connect() as connection:
            trans = connection.begin()
            try:
                for item in updates_list:
                    uid = item['uid']
                    new_price = item['selling_price']

                    # Ambil data lama untuk referensi log
                    old_data = connection.execute(
                        text("SELECT selling_price, solution, brand FROM opportunities WHERE uid = :uid"),
                        {"uid": uid}
                    ).mappings().first()

                    if old_data:
                        old_val = old_data['selling_price'] or 0
                        item_desc = f"{old_data['solution']} ({old_data['brand']})"

                        if float(old_val) != float(new_price):
                            # 1. Update baris tersebut
                            connection.execute(
                                text("UPDATE opportunities SET selling_price = :price, updated_at = NOW() WHERE uid = :uid"),
                                {
                                    "price": float(new_price), # <-- PAKSA JADI PYTHON FLOAT DI SINI
                                    "uid": str(uid)            # <-- PAKSA JADI STRING
                                }
                            )

                            # 2. Catat Log secara spesifik untuk item ini
                            log_q = text("""
                                INSERT INTO activity_logs_sales 
                                (timestamp, opportunity_id, opportunity_name, user_name, action, old_value, new_value)
                                VALUES (NOW(), :oid, :oname, :usr, :act, :old, :new)
                            """)
                            connection.execute(log_q, {
                                "oid": opp_id, "oname": opp_name, "usr": user_name, 
                                "act": f"UPDATE ITEM PRICE - {item_desc}", # Info item digabung ke action
                                "old": str(old_val), "new": str(new_price)
                            })

                trans.commit()
                return {"status": 200, "message": "Harga per item berhasil disimpan."}
            except Exception as e:
                trans.rollback()
                return {"status": 500, "message": f"Gagal menyimpan: {str(e)}"}
    except Exception as e:
        return {"status": 500, "message": str(e)}

# ==============================================================================
# 6. UNIFIED STAGE UPDATE WITH NOTIFICATION
# ==============================================================================

def update_stage_with_notification(opp_id, new_stage, notes, user_actor):
    """
    Fungsi terpadu untuk update stage ke tabel opportunities.
    Jika berubah ke Won/Lost, sistem akan otomatis mengirim email ke Presales.
    """
    try:
        with conn.engine.connect() as connection:
            trans = connection.begin()
            try:
                # 1. AMBIL DATA LAMA
                q_check = text("""
                    SELECT stage, presales_name, opportunity_name, company_name 
                    FROM opportunities 
                    WHERE opportunity_id = :oid 
                    LIMIT 1
                """)
                current_data = connection.execute(q_check, {"oid": opp_id}).mappings().first()
                
                if not current_data:
                    trans.rollback()
                    return {"status": 404, "message": "Opportunity ID not found"}

                old_stage = current_data['stage']
                presales_name = current_data['presales_name']
                opp_name = current_data['opportunity_name']
                comp_name = current_data['company_name']

                # 2. UPDATE STAGE DI DATABASE
                upd_q = text("""
                    UPDATE opportunities 
                    SET stage = :stg, sales_notes = :note, updated_at = NOW() 
                    WHERE opportunity_id = :oid
                """)
                connection.execute(upd_q, {"stg": new_stage, "note": notes, "oid": opp_id})

                # 3. LOG ACTIVITY
                if old_stage != new_stage:
                    log_q = text("""
                        INSERT INTO activity_logs_sales 
                        (timestamp, opportunity_id, opportunity_name, user_name, action, field_changed, old_value, new_value)
                        VALUES (NOW(), :oid, :oname, :usr, 'UPDATE STAGE', 'stage', :old, :new)
                    """)
                    connection.execute(log_q, {
                        "oid": opp_id, "oname": opp_name, "usr": user_actor, 
                        "old": old_stage, "new": new_stage
                    })

                trans.commit()

                # =================================================================
                # 4. LOGIKA NOTIFIKASI EMAIL
                # =================================================================
                target_stages = ['Closed Won', 'Closed Lost']
                
                if new_stage in target_stages and old_stage not in target_stages:
                    q_email = "SELECT email FROM presales WHERE presales_name = :pname LIMIT 1"
                    res_email = conn.query(q_email, params={"pname": presales_name}, ttl=0)
                    
                    if not res_email.empty and res_email.iloc[0]['email']:
                        presales_email = res_email.iloc[0]['email']
                        
                        items_df = conn.query("SELECT solution, brand, cost FROM opportunities WHERE opportunity_id = :oid", params={"oid": opp_id}, ttl=0)
                        email_subject = f"[Action Required] Opportunity {new_stage}: {opp_name}"
                        
                        items_html = "<ul>"
                        for _, item in items_df.iterrows():
                            cost_fmt = f"{float(item['cost']):,.0f}" if pd.notnull(item['cost']) else "0"
                            items_html += f"<li>{item['solution']} ({item['brand']}) - Initial Cost: Rp {cost_fmt}</li>"
                        items_html += "</ul>"

                        email_body = f"""
                        <h3>Status Update: {new_stage.upper()}</h3>
                        <p>Halo <b>{presales_name}</b>,</p>
                        <p>Opportunity berikut telah diubah statusnya menjadi <b>{new_stage}</b> oleh Sales ({user_actor}).</p>
                        <p><b>Customer:</b> {comp_name}<br><b>Opportunity:</b> {opp_name}</p>
                        <p>Mohon segera login ke Presales App dan update <b>Final Cost</b> (Harga Beli/Modal Real) untuk item-item berikut:</p>
                        {items_html}
                        <p><i>Terima kasih,<br>Sales App Automation</i></p>
                        """
                        try:
                            send_email_notification(presales_email, email_subject, email_body)
                        except Exception as e:
                            print(f"⚠️ Email failed: {e}")

                return {"status": 200, "message": f"Stage updated to {new_stage}."}

            except Exception as e:
                trans.rollback()
                return {"status": 500, "message": f"Transaction Error: {str(e)}"}

    except Exception as e:
        return {"status": 500, "message": str(e)}