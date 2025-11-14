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
            # Ambil hanya kolom 'name' dari data yang diterima
            return [user['name'] for user in json_data['data']]
        return []
    except (requests.exceptions.RequestException, json.JSONDecodeError):
        return []

def validate_password(sales_name, password): # <-- UBAH PARAMETER
    """Memvalidasi NAMA & PASSWORD melalui backend."""
    url = f"{APPS_SCRIPT_API_URL}?action=validateAppPassword"
    # Payload sekarang berisi nama dan password
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
    # --- START PERBAIKAN ---
    # Cek jika inputnya adalah DataFrame (dari Kanban)
    if isinstance(data, pd.DataFrame):
        if data.empty:
            return pd.DataFrame()
        # Input sudah berupa DataFrame, kita bisa langsung pakai
        df = data 
    
    # Cek jika inputnya adalah list (dari API)
    elif not data: # Ini aman untuk list
        return pd.DataFrame()
    
    # Jika inputnya list berisi data, konversi ke DataFrame
    else:
        df = pd.DataFrame(data)

    # 1. Tentukan urutan kolom yang Anda inginkan.
    # JIKA TIDAK ADA URUTAN YG DIBERIKAN, GUNAKAN DEFAULT UNTUK TAB 1
    if desired_order is None:
        desired_order = [
            'opportunity_id', 'salesgroup_id', 'sales_name', 'company_name', 'opportunity_name', 'stage', 'selling_price', 'sales_notes'
        ]

    # 2. Filter urutan ideal berdasarkan kolom yang benar-benar ada di DataFrame
    existing_columns_in_order = [col for col in desired_order if col in df.columns]

    # 3. Tambahkan kolom sisa yang tidak ada di daftar 'desired_order' ke bagian akhir
    remaining_columns = [col for col in df.columns if col not in existing_columns_in_order]

    # 4. Gabungkan keduanya untuk mendapatkan urutan final
    final_column_order = existing_columns_in_order # + remaining_columns

    # 5. Terapkan urutan baru ke DataFrame
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
    super_users = ["Ridho Danu S.A", "Budiono Untoro", "Neli Nursyamsyiah", "Tommy S. Purnomo", "Lie Suherman"]
    
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
    ## --- PERUBAHAN DIMULAI DI SINI ---

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
                        
                        # --- INI BAGIAN YANG DIUBAH ---
                        if response.get("status") == 200:
                            st.success("Password successfully changed. You will be redirected to the login page.")
                            # Tunggu sebentar agar user bisa membaca pesan
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
        # Tombol logout di sidebar sudah menangani ini, jadi blok ini hanya untuk error
        return

    st.title(f"Sales App - {sales_group}")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Kanban View", "Search Opportunity", "Update Stage & Notes", "Update Selling Price", "Activity Log"])

    with tab1:
        # 1. Ambil data 'leads' (detail) dan filter
        raw_all_leads_data = get_data('leads', sales_group)
        all_leads_data = filter_data_for_user(raw_all_leads_data, sales_name)

        if not all_leads_data:
            st.info("No data found for your group to display.")
        else:
            df_master = pd.DataFrame(all_leads_data)

            # =============================================================
            # ▼▼▼ LOGIKA KANBAN (SEKARANG DI TAB 1) ▼▼▼
            # =============================================================
            
            # --- 1. LOGIKA NAVIGASI (DETAIL VIEW) --------------------
            # --- 1. LOGIKA NAVIGASI (DETAIL VIEW) --------------------
            if 'selected_kanban_opp_id' in st.session_state:
                
                selected_id = st.session_state.selected_kanban_opp_id
                
                # Tombol "Back"
                if st.button("⬅️ Back to Kanban View"):
                    del st.session_state.selected_kanban_opp_id
                    if 'kanban_stage_message' in st.session_state: del st.session_state.kanban_stage_message
                    if 'kanban_price_message' in st.session_state: del st.session_state.kanban_price_message
                    st.rerun()
                
                opportunity_details_df = df_master[df_master['opportunity_id'] == selected_id]
                
                if opportunity_details_df.empty:
                    st.error(f"Could not find solution details for {selected_id}.")
                else:
                    # Ambil data dari baris pertama untuk ringkasan
                    lead_data = opportunity_details_df.iloc[0].to_dict()
                    opp_name = lead_data.get('opportunity_name', 'N/A')
                    company_name = lead_data.get('company_name', 'N/A')
                    
                    st.header(f"Detail for: {opp_name}")
                    st.subheader(f"Client: {company_name}")
                    
                    # ▼▼▼ BLOK INFO BARU (SEPERTI GAMBAR ANDA) ▼▼▼
                    st.markdown("---")
                    st.subheader("Opportunity Summary")
                    
                    # Tampilkan data ringkasan seperti di gambar
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"👤 **Sales Name:** {lead_data.get('sales_name', 'N/A')}")
                        st.markdown(f"🧑‍💼 **Presales Account Manager:** {lead_data.get('responsible_name', 'N/A')}")
                        st.markdown(f"🏛️ **Pillar:** {lead_data.get('pillar', 'N/A')}")
                        st.markdown(f"🧩 **Solution:** {lead_data.get('solution', 'N/A')}")
                        st.markdown(f"🛠️ **Service:** {lead_data.get('service', 'N/A')}")
                    with col2:
                        st.markdown(f"🏷️ **Brand:** {lead_data.get('brand', 'N/A')}")
                        # Asumsi kolom 'vertical_industry' ada di df_master dari get_data('leads')
                        st.markdown(f"🏭 **Vertical Industry:** {lead_data.get('vertical_industry', 'N/A')}") 
                        st.markdown(f"ℹ️ **Stage:** {lead_data.get('stage', 'N/A')}")
                        st.markdown(f"🆔 **Opportunity ID:** {lead_data.get('opportunity_id', 'N/A')}")
                    st.markdown("---")
                    # ▲▲▲ AKHIR BLOK INFO BARU ▲▲▲

                    # FORM 1: UPDATE STAGE & NOTES
                    st.subheader("Update Opportunity Stage & Notes")
                    with st.form(key="kanban_update_stage_form"):
                        stage_options = ["Open", "Closed Won", "Closed Lost"]
                        current_stage = lead_data.get('stage', 'Open')
                        default_index = stage_options.index(current_stage) if current_stage in stage_options else 0
                        stage = st.selectbox("Stage", options=stage_options, index=default_index)
                        sales_notes = st.text_area("Sales Notes", value=lead_data.get("sales_notes", ""))
                        
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

                    # Tampilkan pesan notifikasi STAGE di sini
                    if 'kanban_stage_message' in st.session_state:
                        msg = st.session_state.kanban_stage_message
                        if msg.get("type") == "success": st.success(msg.get("text"))
                        else: st.error(msg.get("text"))
                        del st.session_state.kanban_stage_message

                    st.markdown("---")
                    # FORM 2: UPDATE SELLING PRICE
                    st.subheader("Update Selling Price per Solution")
                    lines_to_update = opportunity_details_df.to_dict('records')
                    with st.form(key="kanban_update_price_form"):
                        price_inputs = {}
                        for i, item in enumerate(lines_to_update):
                            with st.container(border=True):
                                st.markdown(f"**Solusi {i+1}**")
                                st.write(f"**Pillar:** {item.get('pillar', 'N/A')}")
                                st.write(f"**Solution:** {item.get('solution', 'N/A')}")
                                st.write(f"**Service:** {item.get('service', 'N/A')}")
                                st.write(f"**Brand:** {item.get('brand', 'N/A')}")
                                st.write(f"**Current Selling Price:** {int(item.get('selling_price') or 0):,}")
                                uid = item.get('uid')
                                if not uid:
                                    st.error(f"Error: Solusi {i+1} tidak memiliki UID. Tidak dapat di-update.")
                                    continue
                                current_price = int(item.get('selling_price') or 0)
                                price_inputs[uid] = st.number_input("Input New Selling Price", min_value=0, value=current_price, step=10000, key=f"kanban_price_{uid}")
                        
                        if st.form_submit_button("Update All Selling Prices"):
                            success_count = 0; error_count = 0
                            total_solutions = len(price_inputs)
                            if total_solutions == 0:
                                st.warning("No solutions with valid UID found to update.")
                            else:
                                progress_bar = st.progress(0, text="Memulai update...")
                                for i, (uid, new_price) in enumerate(price_inputs.items()):
                                    response = update_solution_price({"uid": uid, "selling_price": new_price})
                                    if response and response.get("status") == 200: success_count += 1
                                    else: error_count += 1
                                    progress_text = f"Updating price for solution {i+1}/{total_solutions}..."
                                    progress_bar.progress((i + 1) / total_solutions, text=progress_text)
                                
                                progress_bar.empty()
                                msg_text = ""; msg_type = "success"
                                if success_count > 0: msg_text += f"{success_count} of {total_solutions} prices updated. "
                                if error_count > 0: 
                                    msg_text += f"{error_count} of {total_solutions} prices failed."
                                    msg_type = "error" if success_count == 0 else "warning"
                                
                                st.session_state.kanban_price_message = {"type": msg_type, "text": msg_text}
                                st.cache_data.clear()
                                st.rerun()

                    # Tampilkan pesan notifikasi HARGA di sini
                    if 'kanban_price_message' in st.session_state:
                        msg = st.session_state.kanban_price_message
                        msg_type = msg.get("type", "info")
                        if msg_type == "success": st.success(msg.get("text"))
                        elif msg_type == "error": st.error(msg.get("text"))
                        elif msg_type == "warning": st.warning(msg.get("text"))
                        else: st.info(msg.get("text"))
                        del st.session_state.kanban_price_message

            # --- 2. TAMPILAN KANBAN (MAIN VIEW) ----------------------
            else:
                st.subheader("Kanban View by Opportunity Stage")
                st.markdown("Displaying unique data per opportunity with total price. Click 'View Details' on the card.")

                if 'opportunity_id' not in df_master.columns or 'selling_price' not in df_master.columns:
                    st.error("Data 'leads' tidak memiliki 'opportunity_id' or 'selling_price'.")
                    st.stop()
                
                df_master['selling_price'] = pd.to_numeric(df_master['selling_price'], errors='coerce').fillna(0)
                df_sums = df_master.groupby('opportunity_id')['selling_price'].sum().reset_index()
                df_details = df_master.drop_duplicates(subset=['opportunity_id'], keep='first')
                df_details = df_details.drop(columns=['selling_price'])
                df_opps = pd.merge(df_details, df_sums, on='opportunity_id', how='left')

                if 'stage' not in df_opps.columns:
                    st.error("Column 'stage' not found in the data.")
                    st.stop()
                
                df_opps['stage'] = df_opps['stage'].fillna('Open')
                open_opps = df_opps[df_opps['stage'] == 'Open']
                won_opps = df_opps[df_opps['stage'] == 'Closed Won']
                lost_opps = df_opps[df_opps['stage'] == 'Closed Lost']

                col1, col2, col3 = st.columns(3)

                def render_kanban_card(row):
                    with st.container(border=True):
                        st.markdown(f"**{row.get('opportunity_name', 'N/A')}**")
                        st.markdown(f"*{row.get('company_name', 'N/A')}*")
                        st.write(f"Sales: {row.get('sales_name', 'N/A')}")
                        price = int(row.get('selling_price', 0) or 0)
                        st.markdown(f"**Price: {price:,}**")
                        st.caption(f"ID: {row.get('opportunity_id', 'N/A')}")
                        
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
                        sales_notes = st.text_area("Sales Notes", value=lead_data.get("sales_note", ""))
                        
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
        st.header("Update Selling Price per Solution")
        raw_all_opps_price = get_data('leadBySales', sales_group)
        all_opps_price = filter_data_for_user(raw_all_opps_price, sales_name)

        if all_opps_price:
            opp_options_price = {f"{opp.get('opportunity_name', 'N/A')} (ID: {opp.get('opportunity_id')})": opp.get('opportunity_id') for opp in all_opps_price}
            selected_opp_display_price = st.selectbox("Choose Opportunity to Update Price", options=opp_options_price.keys(), index=None, placeholder="Pilih opportunity...")

            if selected_opp_display_price:
                opportunity_id_price = opp_options_price[selected_opp_display_price]
                
                with st.spinner("Fetching solution details..."):
                    # Data detail juga perlu difilter
                    lines_to_update_raw = get_single_lead({"opportunity_id": opportunity_id_price}, sales_group).get('data', [])
                    lines_to_update = filter_data_for_user(lines_to_update_raw, sales_name)
                
                if lines_to_update:
                    with st.form(key="update_price_form"):
                        price_inputs = {}
                        for i, item in enumerate(lines_to_update):
                            with st.container(border=True):
                                st.markdown(f"**Solusi {i+1}**")
                                st.write(f"**Pillar:** {item.get('pillar', 'N/A')}")
                                st.write(f"**Solution:** {item.get('solution', 'N/A')}")
                                st.write(f"**Service:** {item.get('service', 'N/A')}")
                                st.write(f"**Brand:** {item.get('brand', 'N/A')}")
                                st.write(f"**Company:** {item.get('company_name', 'N/A')}")
                                st.write(f"**Current Selling Price:** {int(item.get('selling_price') or 0):,}")
                                uid = item.get('uid', i)
                                current_price = int(item.get('selling_price') or 0)
                                price_inputs[uid] = st.number_input("Input New Selling Price", min_value=0, value=current_price, step=10000, key=f"price_{uid}")
                        
                        if st.form_submit_button("Update All Selling Prices"):
                            success_count = 0
                            error_count = 0
                            total_solutions = len(price_inputs)
                            progress_bar = st.progress(0, text="Memulai update...")

                            for i, (uid, new_price) in enumerate(price_inputs.items()):
                                update_payload = {"uid": uid, "selling_price": new_price}
                                response = update_solution_price(update_payload)
                                if response and response.get("status") == 200:
                                    success_count += 1
                                else:
                                    error_count += 1
                                
                                progress_text = f"Updating price for solution {i+1}/{total_solutions}..."
                                progress_bar.progress((i + 1) / total_solutions, text=progress_text)
                            
                            progress_bar.empty()
                            if success_count > 0: st.success(f"{success_count} from {total_solutions} solution prices successfully updated.")
                            if error_count > 0: st.error(f"{error_count} from {total_solutions} solution prices failed to update.")
                            st.cache_data.clear()
                            st.rerun()
                else:
                    st.warning("No solution details found for this opportunity.")
        else:
            st.warning("Could not load opportunities list for your group.")

    with tab5:
        st.header("Sales Activity Log")
        st.info("Recording changes to Stage, Sales Notes, and Selling Price.")

        if st.button("Refresh Sales Log"):
            st.cache_data.clear()
            st.rerun()

        with st.spinner("Fetching sales activity log..."):
            # Panggil endpoint baru
            log_data_raw = get_data('getSalesActivityLog', sales_group)

            if log_data_raw:
                # Filter log awal berdasarkan peran pengguna (Super user vs user biasa)
                df_log_filtered = pd.DataFrame(filter_data_for_user(log_data_raw, sales_name))

                if not df_log_filtered.empty:
                    
                    # --- LOGIKA FILTER DROPDOWN BERDASARKAN OPPORTUNITY NAME ---
                    if 'OpportunityName' in df_log_filtered.columns and not df_log_filtered['OpportunityName'].empty:
                        opportunity_options = sorted(df_log_filtered['OpportunityName'].dropna().unique().tolist())
                        opportunity_options.insert(0, "All Opportunities")

                        selected_opportunity = st.selectbox(
                            "Filter by Opportunity Name:",
                            options=opportunity_options,
                            key="sales_log_opportunity_filter"
                        )

                        if selected_opportunity != "All Opportunities":
                            df_to_display = df_log_filtered[df_log_filtered['OpportunityName'] == selected_opportunity]
                        else:
                            df_to_display = df_log_filtered
                    else:
                        df_to_display = df_log_filtered
                    # --- AKHIR LOGIKA FILTER DROPDOWN ---

                    # Proses selanjutnya menggunakan df_to_display yang sudah difilter
                    if not df_to_display.empty:
                    # ▼▼▼ BAGIAN INI YANG MELAKUKAN KONVERSI KE WIB ▼▼▼
                    # Mengurutkan dan memformat timestamp ke WIB
                        if 'Timestamp' in df_to_display.columns:
                            df_to_display['Timestamp'] = pd.to_datetime(df_to_display['Timestamp'])
                            df_to_display = df_to_display.sort_values(by="Timestamp", ascending=False)
                            # Ini adalah baris yang mengonversi ke GMT+7 dan memformatnya
                            df_to_display['Timestamp'] = df_to_display['Timestamp'].dt.tz_convert('Asia/Jakarta').dt.strftime('%Y-%m-%d %H:%M:%S')

                        # Mengubah kolom menjadi string untuk mencegah error tampilan
                        for col in ['OldValue', 'NewValue']:
                            if col in df_to_display.columns:
                                df_to_display[col] = df_to_display[col].astype(str)

                        st.write(f"Ditemukan {len(df_to_display)} entri log untuk filter yang dipilih.")
                        st.dataframe(df_to_display)
                    else:
                        st.info("No log activity was recorded for the filter you selected.")
                else:
                    st.info("No log activity was recorded for you.")
            else:
                st.warning("No log activity has been recorded for your group.")

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