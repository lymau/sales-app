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

def validate_password(password):
    """Memvalidasi password melalui backend dan mendapatkan Sales Group."""
    url = f"{APPS_SCRIPT_API_URL}?action=validateAppPassword"
    payload = {"password": password}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        return response.json()
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        return {"status": 500, "message": f"Authentication request error: {e}"}

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
    """Membersihkan data sebelum ditampilkan di st.dataframe."""
    if isinstance(data, pd.DataFrame):
        if data.empty:
            return pd.DataFrame()
        df = data.copy()
    elif not data:
        return pd.DataFrame()
    else:
        df = pd.DataFrame(data)
        
    for col in ['cost', 'selling_price']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df
    

# ANTARMUKA STREAMLIT
# ==============================================================================

# Inisialisasi session state untuk menyimpan data yang sedang di-edit
if 'opportunity_to_update' not in st.session_state:
    st.session_state.opportunity_to_update = None
if 'lines_to_update_price' not in st.session_state:
    st.session_state.lines_to_update_price = None

def main_app():
    sales_group = st.session_state.group_info['salesGroup']
    
    st.title(f"Sales App - {sales_group}")
    st.markdown("---")

    if st.sidebar.button("Logout"):
        st.session_state.group_info = None
        st.cache_data.clear()
        st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs(["View All Opportunities", "Search Opportunity", "Update Stage & Notes", "Update Selling Price"])

    with tab1:
        st.header("All Opportunity Solutions (Detailed View)")
        if st.button("Refresh Opportunities"):
            st.cache_data.clear()

        with st.spinner(f"Fetching opportunities for {sales_group}..."):
            leads_data = get_data('leads', sales_group)
            if leads_data:
                st.write(f"Found {len(leads_data)} solutions.")
                st.dataframe(clean_data_for_display(leads_data))
            else:
                st.info("No opportunities found for your group.")
    
    with tab2:
        st.header("Search Opportunities")
        
        search_keywords = ["Opportunity Name","Company", "Sales Name", "Presales Account Manager", "Pillar", "Solution", "Brand"]
        search_by_option = st.selectbox("Search By", search_keywords, key="search_option")

        search_query = ""
        # Mengambil data yang sudah terfilter untuk mengisi opsi pencarian
        all_leads_data = get_data('leads', sales_group)
        if all_leads_data:
            df_master = pd.DataFrame(all_leads_data)
            if not df_master.empty:
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

        if st.button("Search"):
            if search_query:
                param_map = {
                    "Opportunity Name": "opportunity_name", "Company": "company_name", "Sales Name": "sales_name",
                    "Presales Account Manager": "responsible_name", "Pillar": "pillar",
                    "Solution": "solution", "Brand": "brand"
                }
                search_params = {param_map[search_by_option]: search_query}
                
                with st.spinner(f"Searching for '{search_query}'..."):
                    response = get_single_lead(search_params, sales_group)
                    if response and response.get("status") == 200:
                        found_leads = response.get("data")
                        if found_leads:
                            st.success(f"Found {len(found_leads)} matching solution(s).")
                            st.dataframe(clean_data_for_display(found_leads))
                        else:
                            st.info("No solution found with the given criteria.")
                    else:
                        st.error(response.get("message", "Failed to search."))
            else:
                st.warning("Please select a search term.")

    with tab3:
        st.header("Update Opportunity Stage & Notes")
        all_opps = get_data('leadBySales', sales_group)
        if all_opps:
            opp_options = {f"{opp.get('opportunity_name', 'N/A')} (ID: {opp.get('opportunity_id')})": opp.get('opportunity_id') for opp in all_opps}
            
            selected_opp_display = st.selectbox("Choose Opportunity to Update", options=opp_options.keys(), index=None, placeholder="Pilih opportunity...")

            if selected_opp_display:
                opportunity_id = opp_options[selected_opp_display]
                lead_data = next((item for item in all_opps if item.get('opportunity_id') == opportunity_id), None)

                if lead_data:
                    st.write(f"**Sales Group:** {lead_data.get('salesgroup_id', 'N/A')}")
                    st.write(f"**Sales Name:** {lead_data.get('sales_name', 'N/A')}")

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
                                else:
                                    st.error(response.get("message", "Failed to update."))
        else:
            st.warning("Could not load opportunities list for your group.")

    with tab4:
        st.header("Update Selling Price per Solution")
        all_opps_price = get_data('leadBySales', sales_group)
        if all_opps_price:
            opp_options_price = {f"{opp.get('opportunity_name', 'N/A')} (ID: {opp.get('opportunity_id')})": opp.get('opportunity_id') for opp in all_opps_price}
            
            selected_opp_display_price = st.selectbox("Choose Opportunity to Update Price", options=opp_options_price.keys(), index=None, placeholder="Pilih opportunity...")

            if selected_opp_display_price:
                opportunity_id_price = opp_options_price[selected_opp_display_price]
                
                with st.spinner("Fetching solution details..."):
                    lines_to_update = get_single_lead({"opportunity_id": opportunity_id_price}, sales_group).get('data', [])
                
                if lines_to_update:
                    general_info = lines_to_update[0]
                    st.subheader("Opportunity Details")
                    
                    with st.form(key="update_price_form"):
                        price_inputs = {}
                        for i, item in enumerate(lines_to_update):
                            with st.container(border=True):
                                st.markdown(f"**Solusi {i+1}**")
                                st.write(f"**Pillar:** {item.get('pillar', 'N/A')}")
                                st.write(f"**Solution:** {item.get('solution', 'N/A')}")
                                st.write(f"**Brand:** {item.get('brand', 'N/A')}")
                                st.markdown("---")
                                
                                uid = item.get('uid', i)
                                try:
                                    current_price = int(float(item.get('selling_price')))
                                except (ValueError, TypeError):
                                    current_price = 0

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
    st.info("Please enter the password for your sales group.")

    with st.form("password_form"):
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Enter")

        if submitted:
            with st.spinner("Verifying..."):
                response = validate_password(password)
            
            if response and response.get("status") == 200:
                st.session_state.group_info = response.get("data")
                st.rerun()
            else:
                st.error(response.get("message", "Incorrect password or server error."))

# ==============================================================================
# ROUTER APLIKASI
# ==============================================================================

if st.session_state.group_info:
    main_app()
else:
    password_page()