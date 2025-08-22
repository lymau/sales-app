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

@st.cache_data(ttl=300)
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

def clean_data_for_display(data):
    """
    Membersihkan dan MENGATUR ULANG URUTAN KOLOM data sebelum ditampilkan.
    """
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)

    # 1. Tentukan urutan kolom yang Anda inginkan. Anda bisa mengubah urutan ini.
    desired_order = [
        'opportunity_id', 'salesgroup_id','sales_name', 'company_name', 'vertical_industry', 'opportunity_name', 'responsible_name', 'start_date', 'pillar', 'solution', 'service', 'brand', 'channel', 'distributor_name', 'stage', 'selling_price', 'sales_notes' 
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
                            st.success("Password berhasil diubah. Anda akan dialihkan ke halaman login.")
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

    tab1, tab2, tab3, tab4 = st.tabs(["View All Opportunities", "Search Opportunity", "Update Stage & Notes", "Update Selling Price"])

    with tab1:
        st.header("All Opportunity Solutions (Detailed View)")
        if st.button("Refresh Opportunities"):
            st.cache_data.clear()
            st.rerun()

        with st.spinner(f"Fetching opportunities for {sales_group}..."):
            # 1. Ambil data mentah dari API
            raw_leads_data = get_data('leads', sales_group)
            # 2. Terapkan filter berdasarkan peran pengguna
            leads_data = filter_data_for_user(raw_leads_data, sales_name)
            
            if leads_data:
                st.write(f"Found {len(leads_data)} solutions for you.")
                st.dataframe(clean_data_for_display(leads_data))
            else:
                st.info("No opportunities found for you.")
    
    with tab2:
        st.header("Search Opportunities")
        
        # Ambil data mentah dan filter untuk mengisi opsi pencarian
        raw_all_leads_data = get_data('leads', sales_group)
        all_leads_data = filter_data_for_user(raw_all_leads_data, sales_name)

        if all_leads_data:
            df_master = pd.DataFrame(all_leads_data)
            search_keywords = ["Opportunity Name","Company", "Sales Name", "Presales Account Manager", "Pillar", "Solution", "Brand"]
            search_by_option = st.selectbox("Search By", search_keywords, key="search_option")

            search_query = ""
            if not df_master.empty:
                # Opsi pencarian akan disesuaikan dengan data yang bisa dilihat pengguna
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
                else:
                    col_map = {
                        "Sales Name": "sales_name", "Presales Account Manager": "responsible_name",
                        "Pillar": "pillar", "Solution": "solution", "Brand": "brand"
                    }
                    search_query = st.selectbox(f"Select {search_by_option}", unique_options(col_map.get(search_by_option)), key=f"search_{col_map.get(search_by_option)}", index=None)

        if st.button("Search"):
            if search_query:
                param_map = {
                    "Opportunity Name": "opportunity_name", "Company": "company_name", "Sales Name": "sales_name",
                    "Presales Account Manager": "responsible_name", "Pillar": "pillar",
                    "Solution": "solution", "Brand": "brand"
                }
                search_params = {param_map[search_by_option]: search_query}
                
                with st.spinner(f"Searching for '{search_query}'..."):
                        # Pencarian tetap menggunakan sales_group untuk efisiensi di backend
                        response = get_single_lead(search_params, sales_group)
                        if response and response.get("status") == 200:
                            # Hasil pencarian juga difilter lagi sesuai peran
                            found_leads_raw = response.get("data")
                            found_leads = filter_data_for_user(found_leads_raw, sales_name)
                            
                            if found_leads:
                                st.success(f"Found {len(found_leads)} matching solution(s).")
                                st.dataframe(clean_data_for_display(found_leads))
                            else:
                                st.info("No solution found with the given criteria in your scope.")
                        else:
                            st.error(response.get("message", "Failed to search."))
            else:
                st.warning("Please select a search term.")

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
                                st.write(f"**Brand:** {item.get('brand', 'N/A')}")
                                uid = item.get('uid', i)
                                current_price = int(float(item.get('selling_price', 0)))
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
                            if success_count > 0: st.success(f"{success_count} dari {total_solutions} harga solusi berhasil diupdate.")
                            if error_count > 0: st.error(f"{error_count} dari {total_solutions} harga solusi gagal diupdate.")
                            st.cache_data.clear()
                            st.rerun()
                else:
                    st.warning("No solution details found for this opportunity.")
        else:
            st.warning("Could not load opportunities list for your group.")

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