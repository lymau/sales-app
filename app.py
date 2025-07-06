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

tab1, tab2 = st.tabs(["Lihat Semua Leads", "Update Lead"])

with tab1:
    st.header("Semua Data Leads")
    if st.button("Refresh Leads"):
        with st.spinner("Mengambil semua leads..."):
            response = get_all_leads()
            if response and response.get("status") == 200:
                leads_data = response.get("data")
                if leads_data:
                    st.write(f"Ditemukan {len(leads_data)} leads.")
                    st.dataframe(leads_data)
                else:
                    st.info("Tidak ada data leads ditemukan.")
            else:
                st.error(response.get("message", "Gagal mengambil semua leads."))
                st.json(response)

with tab2:
    st.header("Update Lead")
    uid = st.text_input("Masukkan UID untuk mencari lead", key="uid")
    update_button = st.button("Ambil Data Lead")
    lead = {}
    if update_button and uid:
        with st.spinner(f"Mengambil data lead dengan uid: {uid}..."):
            response = get_single_lead({"uid": uid})
            if response and response.get("status") == 200:
                lead_data = response.get("data")
                if lead_data:
                    lead = lead_data[0]
                    st.write(f"🆔 **Data Lead dengan UID:** {uid}")
                    st.write(f"👤 **Inputter:** {lead.get('presales_name', 'Unknown')}")
                    st.write(f"🧑‍💼 **Account Manager:** {lead.get('responsible_name', 'Unknown')}")
                    st.write(f"🏷️ **Opportunity Name:** {lead.get('opportunity_name', 'Unknown')}")
                    st.write(f"🏛️ **Pillar:** {lead.get('pillar', 'Unknown')}")
                    st.write(f"🧩 **Solution:** {lead.get('solution', 'Unknown')}")
                    st.write(f"🛠️ **Service:** {lead.get('service', 'Unknown')}")
                    st.write(f"🏷️ **Brand:** {lead.get('brand', 'Unknown')}")
                    st.write(f"📡 **Channel:** {lead.get('channel', 'Unknown')}")
                    st.write(f"🏢 **Company:** {lead.get('company_name', 'Unknown')}")
                    st.write(f"🏭 **Vertical Industry:** {lead.get('vertical_industry', 'Unknown')}")
                    st.write(f"💰 **Cost:** {lead.get('cost', 0)}")
                    st.write(f"📝 **Notes:** {lead.get('notes', 'No notes available')}")
                    st.write(f"📅 **Created At:** {lead.get('created_at', 'Unknown')}")
                    st.write(f"⏰ **Updated At:** {lead.get('updated_at', 'Unknown')}")
                else:
                    st.warning("Tidak ada lead ditemukan dengan UUID tersebut.")
            else:
                st.error(response.get("message", "Gagal mengambil data lead."))
                st.json(response)   
    with st.form(key="update_lead_form"):
        # editable fields
        st.subheader("Update Lead Details")

        sales_notes = st.text_area("Catatan (Notes)", height=100, key="update_notes_from_sales")
        selling_price = st.number_input("Selling Price", min_value=0, step=10000, key="update_selling_price")
        stage = st.selectbox("Stage", options=["Open", "Closed Won", "Closed Lost"], key="update_stage")
        submit_button = st.form_submit_button("Update Lead")

        if submit_button:
            update_data = {
                            "uid": uid,
                            "sales_notes": sales_notes,
                            "selling_price": selling_price,
                            "stage": stage,
                        }
            st.write(update_data)
            with st.spinner(f"Memperbarui lead {uid}..."):
                update_response = update_lead(update_data)
                if update_response and update_response.get("status") == 200:
                    st.success(update_response.get("message"))
                else:
                    st.error(update_response.get("message", "Gagal memperbarui lead."))