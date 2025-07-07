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

@st.cache_data(ttl=300) # Data akan di-cache selama 5 menit (300 detik)
def get_master(action: str):
    """
    Mengambil semua data dari sheet 'OBSERVERS' dari API Apps Script.
    Data akan di-cache untuk menghindari panggilan API berulang.
    Args:
        action (str): Tindakan yang ingin dilakukan, misalnya 'getObservers'.
    Returns:
        list: Daftar objek (dict) yang merepresentasikan setiap baris data observers,
              atau list kosong jika terjadi error atau tidak ada data.
    """
    if APPS_SCRIPT_API_URL == "GANTI_DENGAN_URL_WEB_APP_ANDA_DI_SINI":
        st.error("Harap perbarui APPS_SCRIPT_API_URL dengan URL Web App Anda!")
        return []

    url = f"{APPS_SCRIPT_API_URL}?action={action}"
    try:
        response = requests.get(url)
        response.raise_for_status() # Raises an HTTPError for bad responses (4xx or 5xx)
        json_data = response.json()
        if json_data.get("status") == 200:
            return json_data.get("data", [])
        else:
            st.error(f"API Error fetching data: {json_data.get('message', 'Unknown error')}")
            return []
    except requests.exceptions.RequestException as e:
        st.error(f"Network error fetching data: {e}")
        return []
    except json.JSONDecodeError as e:
        st.error(f"JSON decode error fetching data: {e}")
        return []
    

def update_lead(lead_data):
    """
    Mengirimkan data lead yang diperbarui ke endpoint 'update' API Apps Script.

    Args:
        lead_data (dict): Kamus berisi data lead yang akan diperbarui.
                          Wajib menyertakan 'id' dari lead yang akan diubah.

    Returns:
        dict: Respon JSON dari API.
    """
    if APPS_SCRIPT_API_URL == "GANTI_DENGAN_URL_WEB_APP_ANDA_DI_SINI":
        st.error("Harap perbarui APPS_SCRIPT_API_URL dengan URL Web App Anda!")
        return {"status": 500, "message": "Konfigurasi URL API belum lengkap."}

    url = f"{APPS_SCRIPT_API_URL}?action=updateBySales"
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, data=json.dumps(lead_data), headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error saat memperbarui lead: {e}")
        return {"status": 500, "message": f"Request Error: {e}"}
    except json.JSONDecodeError as e:
        st.error(f"Error parsing response JSON: {e}")
        return {"status": 500, "message": f"JSON Decode Error: {e}"}
    

def get_all_leads():
    """
    Mengambil semua data leads dari endpoint 'leads' API Apps Script.

    Returns:
        dict: Respon JSON dari API.
    """
    if APPS_SCRIPT_API_URL == "GANTI_DENGAN_URL_WEB_APP_ANDA_DI_SINI":
        st.error("Harap perbarui APPS_SCRIPT_API_URL dengan URL Web App Anda!")
        return {"status": 500, "message": "Konfigurasi URL API belum lengkap."}

    url = f"{APPS_SCRIPT_API_URL}?action=leads"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error saat mengambil semua leads: {e}")
        return {"status": 500, "message": f"Request Error: {e}"}
    except json.JSONDecodeError as e:
        st.error(f"Error parsing response JSON: {e}")
        return {"status": 500, "message": f"JSON Decode Error: {e}"}
    

def get_single_lead(search_params):
    """
    Mengambil data lead tertentu dari endpoint 'lead' API Apps Script
    berdasarkan parameter pencarian.

    Args:
        search_params (dict): Kamus berisi parameter pencarian (misal: {'id': 'abc'} atau {'email': 'test@example.com'}).

    Returns:
        dict: Respon JSON dari API.
    """
    if APPS_SCRIPT_API_URL == "GANTI_DENGAN_URL_WEB_APP_ANDA_DI_SINI":
        st.error("Harap perbarui APPS_SCRIPT_API_URL dengan URL Web App Anda!")
        return {"status": 500, "message": "Konfigurasi URL API belum lengkap."}

    query_string = "&".join([f"{key}={value}" for key, value in search_params.items()])
    url = f"{APPS_SCRIPT_API_URL}?action=lead&{query_string}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error saat mengambil lead: {e}")
        return {"status": 500, "message": f"Request Error: {e}"}
    except json.JSONDecodeError as e:
        st.error(f"Error parsing response JSON: {e}")
        return {"status": 500, "message": f"JSON Decode Error: {e}"}
    

st.title("Sales App - SISINDOKOM")
st.markdown("---")

tab1, tab2 = st.tabs(["View All Opportunities", "Update Opportunity"])

with tab1:
    st.header("All Opportunities Data")
    if st.button("Refresh Opportunities"):
        with st.spinner("Fetching all opportunities..."):
            response = get_all_leads()
            if response and response.get("status") == 200:
                leads_data = response.get("data")
                if leads_data:
                    st.write(f"Found {len(leads_data)} opportunities.")
                    st.dataframe(leads_data)
                else:
                    st.info("No opportunities found.")
            else:
                st.error(response.get("message", "Failed to fetch opportunities."))
                st.json(response)

with tab2:
    st.header("Update Opportunity")
    opportunity_id = st.text_input("Enter OpportunityID to search opportunity", key="opportunity_id")
    update_button = st.button("Fetch Opportunity Data")
    lead = {}
    if update_button and opportunity_id:
        with st.spinner(f"Mengambil data opportunity dengan id: {opportunity_id}..."):
            response = get_single_lead({"opportunity_id": opportunity_id})
            if response and response.get("status") == 200:
                lead_data = response.get("data")
                if lead_data:
                    lead = lead_data[0]
                    st.write(f"🆔 **Data Opportunity dengan UID:** {opportunity_id}")
                    st.write(f"👤 **Sales Group:** {lead.get('salesgroup_id', 'Unknown')}")
                    st.write(f"👤 **Sales Name:** {lead.get('sales_name', 'Unknown')}")
                    st.write(f"🏷️ **Opportunity Name:** {lead.get('opportunity_name', 'Unknown')}")
                else:
                    st.warning("No opportunity found with the given UID.")
            else:
                st.error(response.get("message", "Failed to fetch opportunity data."))
                st.json(response)
    with st.form(key="update_lead_form"):
        # editable fields
        st.subheader("Update Opportunity Details")

        sales_notes = st.text_area("Notes", value=lead.get("sales_notes", ""), height=100, key="update_notes_from_sales")
        selling_price = st.number_input("Selling Price", min_value=0, step=10000, key="update_selling_price")
        stage = st.selectbox("Stage", options=["Open", "Closed Won", "Closed Lost"], key="update_stage")
        submit_button = st.form_submit_button("Update Opportunity")

        if submit_button:
            update_data = {
                            "opportunity_id": opportunity_id,
                            "sales_notes": sales_notes,
                            "selling_price": selling_price,
                            "stage": stage,
                        }
            st.write(update_data)
            with st.spinner(f"Updating opportunity {opportunity_id}..."):
                update_response = update_lead(update_data)
                if update_response and update_response.get("status") == 200:
                    st.success(update_response.get("message"))
                else:
                    st.error(update_response.get("message", "Failed to update opportunity."))