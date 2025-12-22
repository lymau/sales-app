import streamlit as st
import requests
import json
import pandas as pd

APPS_SCRIPT_API_URL = st.secrets['api_url']

# Konfigurasi halaman aplikasi
st.set_page_config(
    page_title="Sales App - SISINDOKOM",
    page_icon="🔒",
    layout="wide"
)

# Inisialisasi session state untuk menyimpan info grup setelah login
if 'group_info' not in st.session_state:
    st.session_state.group_info = None

# ==============================================================================
# FUNGSI-FUNGSI API (Dengan Caching)
# ==============================================================================

def get_sales_names():
    """Mengambil daftar nama sales dari backend."""
    url = f"{APPS_SCRIPT_API_URL}?action=getSalesNames"
    try:
        response = requests.get(url)
        response.raise_for_status()
        json_data = response.json()
        if json_data.get("status") == 200 and json_data.get("data"):
            return [user['name'] for user in json_data['data']]
        return []
    except (requests.exceptions.RequestException, json.JSONDecodeError):
        return []

def validate_password(sales_name, password):
    """Memvalidasi NAMA & PASSWORD melalui backend."""
    url = f"{APPS_SCRIPT_API_URL}?action=validateAppPassword"
    payload = {"name": sales_name, "password": password} 
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        return response.json()
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        return {"status": 500, "message": f"Authentication request error: {e}"}
    
def change_password(name, old_password, new_password):
    """Mengirim permintaan untuk mengubah password user."""
    url = f"{APPS_SCRIPT_API_URL}?action=changePassword"
    payload = {"name": name, "oldPassword": old_password, "newPassword": new_password}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        return response.json()
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        return {"status": 500, "message": f"Password change request error: {e}"}

@st.cache_data(ttl=600)
def get_data(action: str, sales_group: str):
    """Mengambil data yang sudah difilter berdasarkan sales group."""
    if not APPS_SCRIPT_API_URL or not sales_group: return []
    
    url = f"{APPS_SCRIPT_API_URL}?action={action}&sales_group={sales_group}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        json_data = response.json()
        return json_data.get("data", []) if json_data.get("status") == 200 else []
    except (requests.exceptions.RequestException, json.JSONDecodeError):
        return []

def update_lead_by_sales(lead_data):
    """Mengirimkan update data dari Sales ke endpoint 'updateBySales'."""
    url = f"{APPS_SCRIPT_API_URL}?action=updateBySales"
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, data=json.dumps(lead_data), headers=headers)
        response.raise_for_status()
        return response.json()
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        st.error(f"Error saat memperbarui opportunity: {e}")
        return {"status": 500, "message": f"Request Error: {e}"}

def update_solution_price(solution_data):
    """Mengirimkan update harga untuk satu solusi berdasarkan UID."""
    url = f"{APPS_SCRIPT_API_URL}?action=updateSolutionPrice"
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, data=json.dumps(solution_data), headers=headers)
        response.raise_for_status()
        return response.json()
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        print(f"Error updating solution price: {e}")
        return {"status": 500, "message": f"Request Error: {e}"}

def get_single_lead(search_params, sales_group: str):
    """Mengambil data lead berdasarkan pencarian yang sudah difilter."""
    if not APPS_SCRIPT_API_URL: return {"status": 500, "message": "Konfigurasi URL API belum lengkap."}

    query_string = "&".join([f"{key}={value}" for key, value in search_params.items()])
    if sales_group:
        query_string += f"&sales_group={sales_group}"
        
    url = f"{APPS_SCRIPT_API_URL}?action=lead&{query_string}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        st.error(f"Error saat mengambil lead: {e}")
        return {"status": 500, "message": f"Request Error: {e}"}

def clean_data_for_display(data, desired_order=None):
    """
    Membersihkan dan MENGATUR ULANG URUTAN KOLOM data sebelum ditampilkan.
    """
    if isinstance(data, pd.DataFrame):
        if data.empty:
            return pd.DataFrame()
        df = data 
    
    elif not data:
        return pd.DataFrame()
    
    else:
        df = pd.DataFrame(data)

    if desired_order is None:
        desired_order = [
            'opportunity_id', 'salesgroup_id', 'sales_name', 'company_name', 'opportunity_name', 'stage', 'selling_price', 'sales_notes'
        ]

    
    existing_columns_in_order = [col for col in desired_order if col in df.columns]

    
    remaining_columns = [col for col in df.columns if col not in existing_columns_in_order]


    final_column_order = existing_columns_in_order # + remaining_columns

    
    df = df[final_column_order]

    # Membersihkan tipe data
    for col in ['cost', 'selling_price']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    return df

def filter_data_for_user(data, user_name):
    """
    Memfilter data berdasarkan peran pengguna.
    - Super user (Ridho, Budiono) dapat melihat semua data grup mereka.
    - Pengguna lain hanya dapat melihat data mereka sendiri.
    """
    super_users = ["Ridho Danu S.A", "Budiono Untoro", "Neli Nursyamsyiah", "Tommy S. Purnomo", "Lie Suherman", "Teuku Rangga Pratama"]
    
    if user_name in super_users:
        # Jika super user, kembalikan semua data tanpa filter tambahan
        return data 
    else:
        # Jika bukan super user, filter data berdasarkan 'sales_name'
        return [item for item in data if item.get('sales_name') == user_name]
    

# ANTARMUKA STREAMLIT
# ==============================================================================

# Inisialisasi session state untuk menyimpan data yang sedang di-edit
if 'opportunity_to_update' not in st.session_state:
    st.session_state.opportunity_to_update = None
if 'lines_to_update_price' not in st.session_state:
    st.session_state.lines_to_update_price = None

def main_app():

    # Mengambil data sesi dengan aman
    group_info = st.session_state.get('group_info', {})
    sales_group = group_info.get('salesGroup')
    sales_name = group_info.get('salesName', 'User') # Ambil nama sales, default 'User'

    # Menampilkan informasi user dan tombol logout di sidebar
    with st.sidebar:
        st.subheader(f"Welcome, {sales_name}")
        st.write(f"**Group:** {sales_group}")
        st.markdown("---")
        if st.button("Logout"):
            st.session_state.group_info = None
            st.cache_data.clear()
            st.rerun()

        with st.expander("Change Password"):
            with st.form("change_password_form", clear_on_submit=True):
                old_password = st.text_input("Old Password", type="password", key="old_pass")
                new_password = st.text_input("New Password", type="password", key="new_pass")
                submitted = st.form_submit_button("Update Password")

                if submitted:
                    if not old_password or not new_password:
                        st.warning("Please fill in both password fields.")
                    else:
                        with st.spinner("Updating password..."):
                            response = change_password(sales_name, old_password, new_password)
                        
                        if response.get("status") == 200:
                            st.success("Password successfully changed. You will be redirected to the login page.")
                            import time
                            time.sleep(2) 
                            
                            # Logout pengguna dengan membersihkan session state
                            st.session_state.group_info = None
                            st.cache_data.clear()
                            
                            # Paksa aplikasi untuk menjalankan ulang dari awal (kembali ke halaman login)
                            st.rerun()
                        else:
                            st.error(response.get("message", "Failed to change password."))

    # Pengecekan sesi yang valid
    if not sales_group:
        st.error("Login session is invalid. Please log out and log in again.")
        return

    st.title(f"Sales App - {sales_group}")

    tab1, tab2, tab3, tab4 = st.tabs(["Kanban View", "Search Opportunity", "Update Stage & Notes", "Update Selling Price"])

    with tab1:
        # --- PERUBAHAN 1: AMBIL 2 SUMBER DATA ---
        # 1. leadBySales (Summary): Mengandung Harga Total (Lump Sum) & Stage yang benar.
        # 2. leads (Detail): Mengandung daftar item dan Nama Company.
        
        raw_summary_data = get_data('leadBySales', sales_group)
        summary_data = filter_data_for_user(raw_summary_data, sales_name)

        raw_detail_data = get_data('leads', sales_group)
        detail_data = filter_data_for_user(raw_detail_data, sales_name)

        if not summary_data:
            st.info("No opportunities found for your group to display.")
        else:
            # Siapkan DataFrame Summary (Master untuk Kanban)
            df_summary = pd.DataFrame(summary_data)
            # Pastikan kolom harga numerik
            df_summary['selling_price'] = pd.to_numeric(df_summary['selling_price'], errors='coerce').fillna(0)

            # Siapkan DataFrame Detail (Untuk View Details & Ambil Company Name)
            df_details = pd.DataFrame(detail_data) if detail_data else pd.DataFrame()

            # --- PERUBAHAN 2: MERGE UNTUK DAPATKAN COMPANY NAME ---
            # Kita tempelkan Company Name dari data detail ke data summary
            if not df_details.empty and 'company_name' in df_details.columns:
                company_map = df_details[['opportunity_id', 'company_name']].drop_duplicates(subset=['opportunity_id'])
                df_kanban = pd.merge(df_summary, company_map, on='opportunity_id', how='left')
                df_kanban['company_name'] = df_kanban['company_name'].fillna('Unknown')
            else:
                df_kanban = df_summary
                df_kanban['company_name'] = 'Unknown'

            # =================================================================
            # LOGIKA NAVIGASI (DETAIL VIEW)
            # =================================================================
            if 'selected_kanban_opp_id' in st.session_state:
                
                selected_id = st.session_state.selected_kanban_opp_id
                
                # Tombol Back
                if st.button("⬅️ Back to Kanban View"):
                    del st.session_state.selected_kanban_opp_id
                    if 'kanban_stage_message' in st.session_state: del st.session_state.kanban_stage_message
                    if 'kanban_price_message' in st.session_state: del st.session_state.kanban_price_message
                    st.rerun()
                
                # Ambil data spesifik dari summary (untuk header) dan detail (untuk list item)
                opp_summary = df_kanban[df_kanban['opportunity_id'] == selected_id]
                opp_items = df_details[df_details['opportunity_id'] == selected_id] if not df_details.empty else pd.DataFrame()
                
                if opp_summary.empty:
                    st.error(f"Could not find opportunity details for {selected_id}.")
                else:
                    # Tampilkan Header (Info Project)
                    lead_data = opp_summary.iloc[0].to_dict()
                    opp_name = lead_data.get('opportunity_name', 'N/A')
                    company_name = lead_data.get('company_name', 'N/A')
                    total_price = lead_data.get('selling_price', 0)
                    
                    st.header(f"Detail for: {opp_name}")
                    st.subheader(f"Client: {company_name}")
                    st.write(f"**Total Project Value:** {int(total_price):,}")
                    
                    st.markdown("---")
                    
                    # Tampilkan Detail Item (Hanya Read-Only / Tabel Saja)
                    st.subheader("Solution Components")
                    if not opp_items.empty:
                        # Tampilkan tabel solusi
                        display_cols = ['pillar', 'solution', 'service', 'brand']
                        # Filter kolom yang ada saja
                        final_cols = [c for c in display_cols if c in opp_items.columns]
                        st.dataframe(opp_items[final_cols], use_container_width=True)
                    else:
                        st.info("No detailed items found for this opportunity.")

                    st.markdown("---")

                    # FORM UPDATE STAGE & NOTES
                    st.subheader("Update Stage & Notes")
                    with st.form(key="kanban_update_stage_form"):
                        stage_options = ["Open", "Closed Won", "Closed Lost"]
                        current_stage = lead_data.get('stage', 'Open')
                        default_index = stage_options.index(current_stage) if current_stage in stage_options else 0
                        
                        stage = st.selectbox("Stage", options=stage_options, index=default_index)
                        sales_notes = st.text_area("Sales Notes", value=lead_data.get("sales_notes", "")) # Perhatikan: sales_notes vs sales_note di backend
                        
                        if st.form_submit_button("Update Stage & Notes"):
                            update_data = {"opportunity_id": selected_id, "sales_notes": sales_notes, "stage": stage}
                            with st.spinner(f"Updating opportunity {selected_id}..."):
                                response = update_lead_by_sales(update_data)
                                if response and response.get("status") == 200:
                                    st.session_state.kanban_stage_message = {"type": "success", "text": response.get("message")}
                                    st.cache_data.clear()
                                    st.rerun()
                                else:
                                    st.error(response.get("message", "Failed to update."))

                    if 'kanban_stage_message' in st.session_state:
                        msg = st.session_state.kanban_stage_message
                        if msg.get("type") == "success": st.success(msg.get("text"))
                        else: st.error(msg.get("text"))
                        del st.session_state.kanban_stage_message

            # =================================================================
            # TAMPILAN KANBAN (MAIN VIEW)
            # =================================================================
            else:
                st.subheader("Kanban View by Opportunity Stage")
                st.markdown("Showing Lump Sum Price per Opportunity.")
                
                # --- PERUBAHAN 3: MENGGUNAKAN df_kanban YANG SUDAH JADI ---
                # Tidak ada lagi groupby().sum() karena df_kanban sudah berisi total price
                
                if 'stage' not in df_kanban.columns:
                    df_kanban['stage'] = 'Open'

                open_opps = df_kanban[df_kanban['stage'] == 'Open']
                won_opps = df_kanban[df_kanban['stage'] == 'Closed Won']
                lost_opps = df_kanban[df_kanban['stage'] == 'Closed Lost']

                col1, col2, col3 = st.columns(3)

                def render_kanban_card(row):
                    with st.container(border=True):
                        st.markdown(f"**{row.get('opportunity_name', 'N/A')}**")
                        st.markdown(f"*{row.get('company_name', 'N/A')}*")
                        st.caption(f"Sales: {row.get('sales_name', 'N/A')}")
                        
                        # Harga langsung dari row summary
                        price = int(row.get('selling_price', 0) or 0)
                        st.markdown(f"**Price: {price:,}**")
                        
                        opp_id = row.get('opportunity_id')
                        if st.button(f"View Details", key=f"btn_detail_{opp_id}"):
                            st.session_state.selected_kanban_opp_id = opp_id
                            st.rerun()

                with col1:
                    st.markdown(f"### 🧊 Open ({len(open_opps)})")
                    st.markdown("---")
                    for _, row in open_opps.iterrows():
                        render_kanban_card(row)

                with col2:
                    st.markdown(f"### ✅ Closed Won ({len(won_opps)})")
                    st.markdown("---")
                    for _, row in won_opps.iterrows():
                        render_kanban_card(row)

                with col3:
                    st.markdown(f"### ❌ Closed Lost ({len(lost_opps)})")
                    st.markdown("---")
                    for _, row in lost_opps.iterrows():
                        render_kanban_card(row)
    
    with tab2:
        st.header("Search Opportunities")
        
        raw_all_leads_data = get_data('leads', sales_group)
        all_leads_data = filter_data_for_user(raw_all_leads_data, sales_name)

        if all_leads_data:
            df_master = pd.DataFrame(all_leads_data)
            # Remove "Kanban by Stage" from this list
            search_keywords = ["Opportunity Name","Company", "Sales Name", "Presales Account Manager", "Pillar", "Solution", "Brand", "Stage"]
            search_by_option = st.selectbox("Search By", search_keywords, key="search_option", index=None, placeholder="Select search mode...")

            # Logika pencarian standar
            if search_by_option is not None:
                search_query = ""
                if not df_master.empty:
                    unique_options = lambda col: sorted(df_master[col].unique()) if col in df_master else []
                    if search_by_option == "Opportunity Name":
                        options = sorted(df_master['opportunity_name'].unique())
                        search_query = st.selectbox("Select Opportunity Name", options, key="search_opportunity_name", index=None)
                    elif search_by_option == "Company":
                        options = sorted(df_master['company_name'].unique())
                        search_query = st.selectbox("Select Company", options, key="search_company", index=None)
                    elif search_by_option == "Sales Name":
                        options = sorted(df_master['sales_name'].unique())
                        search_query = st.selectbox("Select Sales Name", options, key="search_sales_name", index=None)
                    elif search_by_option == "Presales Account Manager":
                        options = sorted(df_master['responsible_name'].unique())
                        search_query = st.selectbox("Select Presales Account Manager", options, key="search_presales_am", index=None)
                    elif search_by_option == "Pillar":
                        options = sorted(df_master['pillar'].unique())
                        search_query = st.selectbox("Select Pillar", options, key="search_pillar", index=None)
                    elif search_by_option == "Solution":
                        options = sorted(df_master['solution'].unique())
                        search_query = st.selectbox("Select Solution", options, key="search_solution", index=None)
                    elif search_by_option == "Brand":
                        options = sorted(df_master['brand'].unique())
                        search_query = st.selectbox("Select Brand", options, key="search_brand", index=None)
                    elif search_by_option == "Stage":
                        options = sorted(df_master['stage'].unique())
                        search_query = st.selectbox("Select Stage", options, key="search_stage", index=None)
                    else:
                        col_map = {
                            "Sales Name": "sales_name", "Presales Account Manager": "responsible_name",
                            "Pillar": "pillar", "Solution": "solution", "Brand": "brand", "Stage": "stage"
                        }
                        search_query = st.selectbox(f"Select {search_by_option}", unique_options(col_map.get(search_by_option)), key=f"search_{col_map.get(search_by_option)}", index=None)

                if st.button("Search"):
                    if search_query:
                        param_map = {
                            "Opportunity Name": "opportunity_name", "Company": "company_name", "Sales Name": "sales_name",
                            "Presales Account Manager": "responsible_name", "Pillar": "pillar",
                            "Solution": "solution", "Brand": "brand", "Stage": "stage"
                        }
                        search_params = {param_map[search_by_option]: search_query}
                        
                        with st.spinner(f"Searching for '{search_query}'..."):
                                response = get_single_lead(search_params, sales_group)
                                if response and response.get("status") == 200:
                                    found_leads_raw = response.get("data")
                                    found_leads = filter_data_for_user(found_leads_raw, sales_name)
                                    
                                    if found_leads:
                                        st.success(f"Found {len(found_leads)} matching solution(s).")
                                        search_result_columns = [
                                            'opportunity_id', 'sales_name', 'company_name', 'opportunity_name', 
                                            'stage', 'selling_price', 'sales_notes', 
                                            'pillar', 'solution', 'service', 'brand' 
                                        ]
                                        st.dataframe(clean_data_for_display(found_leads, desired_order=search_result_columns))
                                    else:
                                        st.info("No solution found with the given criteria in your scope.")
                                else:
                                    st.error(response.get("message", "Failed to search."))
                    else:
                        st.warning("Please select a search term.")
        else:
            st.info("No data found for your group to search or display.")

    with tab3:
        st.header("Update Opportunity Stage & Notes")
        raw_all_opps = get_data('leadBySales', sales_group)
        all_opps = filter_data_for_user(raw_all_opps, sales_name)

        if all_opps:
            opp_options = {f"{opp.get('opportunity_name', 'N/A')} (ID: {opp.get('opportunity_id')})": opp.get('opportunity_id') for opp in all_opps}
            selected_opp_display = st.selectbox("Choose Opportunity to Update", options=opp_options.keys(), index=None, placeholder="Pilih opportunity...")

            if selected_opp_display:
                opportunity_id = opp_options[selected_opp_display]
                lead_data = next((item for item in all_opps if item.get('opportunity_id') == opportunity_id), None)

                if lead_data:
                    with st.form(key="update_stage_form"):
                        stage_options = ["Open", "Closed Won", "Closed Lost"]
                        current_stage = lead_data.get('stage', 'Open')
                        default_index = stage_options.index(current_stage) if current_stage in stage_options else 0
                        stage = st.selectbox("Stage", options=stage_options, index=default_index)
                        sales_notes = st.text_area("Sales Notes", value=lead_data.get("sales_note", ""), placeholder="Please inform the reason for stage change. E.g., Why the opportunity is Won or Lost.")
                        
                        if st.form_submit_button("Update Stage & Notes"):
                            update_data = {"opportunity_id": opportunity_id, "sales_notes": sales_notes, "stage": stage}
                            with st.spinner(f"Updating opportunity {opportunity_id}..."):
                                response = update_lead_by_sales(update_data)
                                if response and response.get("status") == 200:
                                    st.success(response.get("message"))
                                    st.cache_data.clear()
                                    st.rerun()
                                else:
                                    st.error(response.get("message", "Failed to update."))
        else:
            st.warning("Could not load opportunities list for you.")

    with tab4:
        st.header("Update Opportunity Selling Price (Lump Sum)")
        st.info("Update total project value directly. This will update the Sales Dashboard.")

        # 1. Ambil data dari endpoint 'leadBySales' (Data Summary/Header)
        # Ini lebih ringan daripada mengambil detail leads
        raw_sales_opps = get_data('leadBySales', sales_group)
        sales_opps = filter_data_for_user(raw_sales_opps, sales_name)

        if sales_opps:
            # Buat dictionary untuk dropdown: "Nama Opp (ID)" -> ID
            opp_options = {f"{item.get('opportunity_name', 'N/A')} ({item.get('opportunity_id')})": item.get('opportunity_id') for item in sales_opps}
            
            selected_display = st.selectbox("Select Opportunity", options=opp_options.keys(), index=None, placeholder="Choose an opportunity...")

            if selected_display:
                selected_id = opp_options[selected_display]
                
                # Ambil data saat ini dari list yang sudah ditarik
                current_data = next((item for item in sales_opps if item['opportunity_id'] == selected_id), None)
                
                if current_data:
                    current_price = float(current_data.get('selling_price') or 0)
                    opp_name = current_data.get('opportunity_name')
                    
                    st.markdown(f"**Selected Opportunity:** {opp_name}")
                    st.markdown(f"**Current Total Price:** Rp {current_price:,.0f}")
                    st.markdown("---")

                    with st.form("lump_sum_price_form"):
                        # Input Harga Baru
                        new_price = st.number_input("New Total Selling Price", min_value=0.0, value=current_price, step=1000000.0, format="%.0f")
                        
                        submitted = st.form_submit_button("Update Price")
                        
                        if submitted:
                            # Payload Data
                            payload = {
                                "opportunity_id": selected_id,
                                "selling_price": new_price,
                                "user": sales_name
                            }
                            
                            # Kirim Request ke Action Baru di GAS
                            with st.spinner("Updating price..."):
                                url = f"{APPS_SCRIPT_API_URL}?action=updateLumpSumPrice"
                                headers = {"Content-Type": "application/json"}
                                try:
                                    response = requests.post(url, data=json.dumps(payload), headers=headers)
                                    
                                    if response.status_code == 200:
                                        res_json = response.json()
                                        if res_json.get("status") == 200:
                                            st.success("Price updated successfully!")
                                            st.cache_data.clear() # Hapus cache agar data terbaru muncul
                                            import time
                                            time.sleep(1)
                                            st.rerun()
                                        else:
                                            st.error(f"Failed: {res_json.get('message')}")
                                    else:
                                        st.error(f"HTTP Error: {response.status_code}")
                                except Exception as e:
                                    st.error(f"Connection Error: {e}")
                else:
                    st.error("Data integrity error: Opportunity ID found in list but details missing.")
        else:
            st.warning("No opportunities found for your group.")

# ==============================================================================
# HALAMAN INPUT PASSWORD
# ==============================================================================

def password_page():
    """Menampilkan halaman untuk input password."""
    st.header("Sales App Authentication")
    st.info("Please select your name and enter your password.")

    sales_names = get_sales_names()
    if not sales_names:
        st.error("Could not load sales user list. Please check the backend connection.")
        return

    with st.form("password_form"):
        selected_name = st.selectbox("Select Your Name", options=sorted(sales_names))
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Enter")

        if submitted:
            if not selected_name or not password:
                st.warning("Please select your name and enter your password.")
            else:
                with st.spinner("Verifying..."):
                    response = validate_password(selected_name, password)
                
                if response and response.get("status") == 200:
                    st.session_state.group_info = response.get("data")
                    st.rerun()
                else:
                    st.error(response.get("message", "Incorrect credentials or server error."))

# ==============================================================================
# ROUTER APLIKASI
# ==============================================================================

if st.session_state.get('group_info'):
    main_app()
else:
    password_page()