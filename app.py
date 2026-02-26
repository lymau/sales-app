import streamlit as st
import utils
import backend as db

st.set_page_config(page_title="Sales App - SISINDOKOM", page_icon="🔒", layout="wide")

# Session State
if 'group_info' not in st.session_state: st.session_state.group_info = None
if 'selected_kanban_opp_id' not in st.session_state: st.session_state.selected_kanban_opp_id = None

# Super Users
SUPER_USERS = ["Ridho Danu S.A", "Budiono Untoro", "Neli Nursyamsyiah", "Tommy S. Purnomo", "Lie Suherman", "Ridha Evitafany"]

def login_page():
    st.title("🔐 Sales App Login")
    sales_list = db.get_sales_names()
    with st.form("login"):
        user_in = st.selectbox("Nama Sales", options=sales_list)
        pass_in = st.text_input("Password", type="password")
        if st.form_submit_button("Masuk"):
            res = db.validate_user(user_in, pass_in)
            if res['status'] == 200:
                st.session_state.group_info = res['data']
                st.rerun()
            else:
                st.error(res['message'])

def main_app():
    group = st.session_state.group_info
    sales_name = group.get('salesName')
    sales_group = group.get('salesGroup')
    is_super = sales_name in SUPER_USERS

    with st.sidebar:
        st.write(f"👤 **{sales_name}**")
        st.caption(f"Group: {sales_group}")
        if is_super: st.success("🌟 Manager Mode")
        if st.button("Logout", type="primary"):
            st.session_state.group_info = None
            st.rerun()

    st.title(f"Sales App - {sales_group}")
    
    t1, t2, t3, t4 = st.tabs(["Kanban", "Search", "Update Stage", "Update Price"])
    
    with t1: utils.tab1_kanban(sales_group, sales_name, is_super)
    with t2: utils.tab2_dashboard(sales_group, sales_name, is_super)
    with t3: utils.tab3_update_stage(sales_group, sales_name, is_super)
    with t4: utils.tab4_update_price(sales_group, sales_name, is_super)

if st.session_state.group_info:
    main_app()
else:
    login_page()