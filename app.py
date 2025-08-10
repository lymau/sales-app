import streamlit as st
import requests
import json
import pandas as pd

APPS_SCRIPT_API_URL = st.secrets['api_url']

st.set_page_config(
    page_title="Sales App - SISINDOKOM",
    page_icon=":clipboard:",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# FUNGSI-FUNGSI API (Dengan Caching)
# ==============================================================================

@st.cache_data(ttl=450) # Cache data master selama 5 menit
def get_master(action: str):
    """Mengambil data master dari API Google Apps Script."""
    if not APPS_SCRIPT_API_URL or APPS_SCRIPT_API_URL == "GANTI_DENGAN_URL_WEB_APP_ANDA_DI_SINI":
        st.error("URL API belum dikonfigurasi di st.secrets!")
        return []
    
    url = f"{APPS_SCRIPT_API_URL}?action={action}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        json_data = response.json()
        if json_data.get("status") == 200:
            return json_data.get("data", [])
        else:
            # Tidak menampilkan error di sini agar tidak mengganggu UI jika hanya satu API call yg gagal
            print(f"API Error fetching {action}: {json_data.get('message', 'Unknown error')}")
            return []
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        print(f"Network/JSON error fetching {action}: {e}")
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

def get_all_sales_leads():
    """Mengambil semua data opportunity dari perspektif Sales."""
    # Menggunakan endpoint 'leadBySales' yang mengambil data dari sheet 'sales_oppty_q3'
    return get_master('leadBySales')

# PERBAIKAN: Fungsi ini dibuat mandiri dan tidak menggunakan get_master()
# untuk menghindari potensi masalah cache dan untuk kejelasan kode.
def get_single_opportunity_details(opportunity_id):
    """Mengambil detail semua product line untuk satu opportunity_id."""
    if not APPS_SCRIPT_API_URL or APPS_SCRIPT_API_URL == "GANTI_DENGAN_URL_WEB_APP_ANDA_DI_SINI":
        return []
    
    # URL dibuat secara eksplisit dengan parameter yang benar
    url = f"{APPS_SCRIPT_API_URL}?action=lead&opportunity_id={opportunity_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        json_data = response.json()
        if json_data.get("status") == 200:
            return json_data.get("data", [])
        else:
            # Tidak menampilkan st.error agar tidak mengganggu UI
            print(f"API Error fetching single opportunity: {json_data.get('message', 'Unknown error')}")
            return []
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        print(f"Network/JSON error fetching single opportunity: {e}")
        return []

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

def get_single_lead(search_params):
    """Mengambil data lead tertentu dari API berdasarkan parameter pencarian."""
    if not APPS_SCRIPT_API_URL or APPS_SCRIPT_API_URL == "GANTI_DENGAN_URL_WEB_APP_ANDA_DI_SINI":
        return {"status": 500, "message": "Konfigurasi URL API belum lengkap."}

    query_string = "&".join([f"{key}={value}" for key, value in search_params.items()])
    url = f"{APPS_SCRIPT_API_URL}?action=lead&{query_string}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        st.error(f"Error saat mengambil lead: {e}")
        return {"status": 500, "message": f"Request Error: {e}"}

def clean_data_for_display(data):
    """Membersihkan data sebelum ditampilkan di st.dataframe untuk mencegah error."""
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    for col in ['cost', 'selling_price']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df
    

# ANTARMUKA STREAMLIT
# ==============================================================================

st.title("Sales App - SISINDOKOM")
st.markdown("---")

# Inisialisasi session state untuk menyimpan data yang sedang di-edit
if 'opportunity_to_update' not in st.session_state:
    st.session_state.opportunity_to_update = None
if 'lines_to_update_price' not in st.session_state:
    st.session_state.lines_to_update_price = None

# Definisi Tab
tab1, tab2, tab3, tab4 = st.tabs(["View All Opportunities", "Search Opportunity", "Update Stage & Notes", "Update Selling Price"])

# === TAB 1: MELIHAT SEMUA DATA ===
with tab1:
    st.header("All Opportunities Data (Sales View)")
    if st.button("Refresh Opportunities"):
        with st.spinner("Fetching all opportunities..."):
            leads_data = get_all_sales_leads()
            if leads_data:
                st.write(f"Found {len(leads_data)} opportunities.")
                # Menggunakan DataFrame untuk tampilan yang lebih baik dan pembersihan data
                df = pd.DataFrame(leads_data)
                if 'selling_price' in df.columns:
                    df['selling_price'] = pd.to_numeric(df['selling_price'], errors='coerce').fillna(0)
                st.dataframe(df)
            else:
                st.info("No opportunities found.")

with tab2:
    st.header("Search Opportunities")
    
    search_keywords = [
        "Opportunity Name", "Company", "Sales Group", "Sales Name", 
        "Presales Account Manager", "Pillar", "Solution", "Brand"
    ]
    search_by_option = st.selectbox("Search By", search_keywords, key="search_option")

    search_query = ""
    if search_by_option == "Opportunity Name":
        options = sorted([opt.get("Desc", "") for opt in get_master('getOpportunities')])
        search_query = st.selectbox("Select Opportunity Name", options, key="search_opp_name", index=None)
    elif search_by_option == "Company":
        options = sorted([opt.get("Company", "") for opt in get_master('getCompanies')])
        search_query = st.selectbox("Select Company", options, key="search_company", index=None)
    elif search_by_option == "Sales Group":
        # PERBAIKAN: Menggunakan set untuk mendapatkan nilai unik
        options = sorted(list(set([opt.get("SalesGroup", "") for opt in get_master('getSalesGroups')])))
        search_query = st.selectbox("Select Sales Group", options, key="search_sales_group", index=None)
    elif search_by_option == "Sales Name":
        options = sorted(list(set([opt.get("SalesName", "") for opt in get_master('getSalesGroups')])))
        search_query = st.selectbox("Select Sales Name", options, key="search_sales_name", index=None)
    elif search_by_option == "Presales Account Manager":
        options = sorted([opt.get("Responsible", "") for opt in get_master('getResponsibles')])
        search_query = st.selectbox("Select Presales Account Manager", options, key="search_presales_am", index=None)
    elif search_by_option == "Pillar":
        options = sorted(list(set([opt.get("Pillar", "") for opt in get_master('getPillars')])))
        search_query = st.selectbox("Select Pillar", options, key="search_pillar", index=None)
    elif search_by_option == "Solution":
        options = sorted(list(set([opt.get("Solution", "") for opt in get_master('getPillars')])))
        search_query = st.selectbox("Select Solution", options, key="search_solution", index=None)
    elif search_by_option == "Brand":
        options = sorted([opt.get("Brand", "") for opt in get_master('getBrands')])
        search_query = st.selectbox("Select Brand", options, key="search_brand", index=None)

    if st.button("Search"):
        if search_query:
            param_map = {
                "Opportunity Name": "opportunity_name", "Company": "company_name",
                "Sales Group": "salesgroup_id", "Sales Name": "sales_name",
                "Presales Account Manager": "responsible_name", "Pillar": "pillar",
                "Solution": "solution", "Brand": "brand"
            }
            search_params = {param_map[search_by_option]: search_query}
            
            with st.spinner(f"Searching for '{search_query}' in '{search_by_option}'..."):
                response = get_single_lead(search_params)
                if response and response.get("status") == 200:
                    found_leads = response.get("data")
                    if found_leads:
                        st.success(f"Found {len(found_leads)} matching opportunity/ies.")
                        st.dataframe(clean_data_for_display(found_leads))
                    else:
                        st.info("No opportunity found with the given criteria.")
                else:
                    st.error(response.get("message", "Failed to search opportunity."))
        else:
            st.warning("Please select a search term.")

with tab3:
    st.header("Update Opportunity Stage & Notes")
    
    # Ambil daftar opportunity untuk dipilih
    all_opps = get_all_sales_leads()
    if all_opps:
        # Buat daftar pilihan yang lebih informatif: "Opportunity Name (ID: ...)"
        opp_options = {f"{opp.get('opportunity_name', 'N/A')} (ID: {opp.get('opportunity_id')})": opp.get('opportunity_id') for opp in all_opps}
        
        selected_opp_display = st.selectbox(
            "Choose Opportunity to Update",
            options=opp_options.keys(),
            index=None,
            placeholder="Pilih opportunity..."
        )

        if selected_opp_display:
            # Dapatkan opportunity_id dari pilihan
            opportunity_id = opp_options[selected_opp_display]
            
            # Cari data lengkap untuk opportunity yang dipilih
            lead_data = next((item for item in all_opps if item.get('opportunity_id') == opportunity_id), None)

            if lead_data:
                st.write(f"**Sales Group:** {lead_data.get('salesgroup_id', 'N/A')}")
                st.write(f"**Sales Name:** {lead_data.get('sales_name', 'N/A')}")

                with st.form(key="update_stage_form"):
                    st.subheader("Update Details")
                    
                    # Tentukan index default untuk stage
                    stage_options = ["Open", "Closed Won", "Closed Lost"]
                    current_stage = lead_data.get('stage', 'Open')
                    default_index = stage_options.index(current_stage) if current_stage in stage_options else 0

                    stage = st.selectbox("Stage", options=stage_options, index=default_index)
                    sales_notes = st.text_area("Sales Notes", value=lead_data.get("sales_note", ""))
                    
                    submit_button = st.form_submit_button("Update Stage & Notes")

                    if submit_button:
                        update_data = {
                            "opportunity_id": opportunity_id,
                            "sales_notes": sales_notes,
                            "stage": stage,
                        }
                        with st.spinner(f"Updating opportunity {opportunity_id}..."):
                            update_response = update_lead_by_sales(update_data)
                            if update_response and update_response.get("status") == 200:
                                st.success(update_response.get("message"))
                                # Clear cache agar data terbaru bisa diambil lagi
                                st.cache_data.clear()
                            else:
                                st.error(update_response.get("message", "Failed to update opportunity."))
    else:
        st.warning("Could not load opportunities list.")

with tab4:
    st.header("Update Selling Price per Solution")

    all_opps_price = get_all_sales_leads()
    if all_opps_price:
        opp_options_price = {f"{opp.get('opportunity_name', 'N/A')} (ID: {opp.get('opportunity_id')})": opp.get('opportunity_id') for opp in all_opps_price}
        
        selected_opp_display_price = st.selectbox(
            "Choose Opportunity to Update Price",
            options=opp_options_price.keys(),
            index=None,
            placeholder="Pilih opportunity..."
        )

        if selected_opp_display_price:
            opportunity_id_price = opp_options_price[selected_opp_display_price]
            
            with st.spinner("Fetching solution details..."):
                lines_to_update = get_single_opportunity_details(opportunity_id_price)
            
            if lines_to_update:
                general_info = lines_to_update[0]
                st.subheader("Opportunity Details")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Sales Group:** {general_info.get('salesgroup_id', 'N/A')}")
                    st.write(f"**Sales Name:** {general_info.get('sales_name', 'N/A')}")
                    st.write(f"**Presales Account Manager:** {general_info.get('responsible_name', 'N/A')}")
                with col2:
                    st.write(f"**Opportunity Name:** {general_info.get('opportunity_name', 'N/A')}")
                    st.write(f"**Company:** {general_info.get('company_name', 'N/A')}")
                    st.write(f"**Vertical Industry:** {general_info.get('vertical_industry', 'N/A')}")
                
                st.markdown("---")
                st.info(f"Ditemukan {len(lines_to_update)} solusi untuk opportunity ini. Silakan update harga jual di bawah.")
                
                with st.form(key="update_price_form"):
                    price_inputs = {}
                    
                    for i, item in enumerate(lines_to_update):
                        with st.container(border=True):
                            st.markdown(f"**Solusi {i+1}**")
                            st.write(f"**Pillar:** {item.get('pillar', 'N/A')}")
                            st.write(f"**Solution:** {item.get('solution', 'N/A')}")
                            st.write(f"**Service:** {item.get('service', 'N/A')}")
                            st.write(f"**Brand:** {item.get('brand', 'N/A')}")
                            st.write(f"**Channel:** {item.get('channel', 'N/A')}")
                            st.write(f"**Selling Price:** {item.get('selling_price', 'N/A')}")
                            st.markdown("---")
                            
                            uid = item.get('uid', i)

                            # PERBAIKAN: Logika untuk menangani nilai kosong atau tidak valid
                            try:
                                # Coba konversi ke float dulu untuk menangani angka desimal, lalu ke int
                                current_price = int(float(item.get('selling_price')))
                            except (ValueError, TypeError):
                                # Jika gagal (misal: nilainya '' atau None), default ke 0
                                current_price = 0

                            price_inputs[uid] = st.number_input(
                                "Input New Selling Price", 
                                min_value=0, 
                                value=current_price,
                                step=10000,
                                key=f"price_{uid}"
                            )
                    
                    submitted = st.form_submit_button("Update All Selling Prices")
                    
                    if submitted:
                        success_count = 0
                        error_count = 0
                        total_solutions = len(price_inputs)
                        progress_bar = st.progress(0, text="Memulai update...")

                        for i, (uid, new_price) in enumerate(price_inputs.items()):
                            update_payload = {
                                "uid": uid,
                                "selling_price": new_price
                            }
                            
                            response = update_solution_price(update_payload)
                            if response and response.get("status") == 200:
                                success_count += 1
                            else:
                                error_count += 1
                            
                            progress_text = f"Updating price for solution {i+1}/{total_solutions}..."
                            progress_bar.progress((i + 1) / total_solutions, text=progress_text)
                        
                        progress_bar.empty()

                        if success_count > 0:
                            st.success(f"{success_count} dari {total_solutions} harga solusi berhasil diupdate.")
                        if error_count > 0:
                            st.error(f"{error_count} dari {total_solutions} harga solusi gagal diupdate.")
                        
                        st.cache_data.clear()
            else:
                st.warning("No solution details found for this opportunity.")
    else:
        st.warning("Could not load opportunities list.")