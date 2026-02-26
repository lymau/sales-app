import streamlit as st
import pandas as pd
import time
import backend as db

def format_idr(value):
    """Format angka ke format Rupiah (e.g., 1.000.000)."""
    try:
        if value is None: return "0"
        val_float = float(value)
        return f"{val_float:,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return "0"

# ==============================================================================
# FRAGMENT TABS
# ==============================================================================

@st.fragment
def tab1_kanban(sales_group, sales_name, is_super):
    st.header("Kanban View")
    
    # Load Data
    df_kanban = db.get_kanban_data(sales_group, sales_name, is_super)

    if df_kanban.empty:
        msg = f"Tim {sales_group} belum memiliki opportunity." if is_super else "Anda belum memiliki opportunity."
        st.info(msg)
        return

    # --- Dashboard Metrics ---
    total_value = df_kanban['selling_price'].sum()
    total_opps = df_kanban['opportunity_id'].nunique()
    won_val = df_kanban[df_kanban['stage'] == 'Closed Won']['selling_price'].sum()

    m1, m2, m3 = st.columns(3)
    m1.metric("Pipeline Value", f"Rp {format_idr(total_value)}")
    m2.metric("Total Opportunities", f"{total_opps}")
    m3.metric("Won Value", f"Rp {format_idr(won_val)}")
    st.divider()

    # --- Detail View Logic ---
    if st.session_state.selected_kanban_opp_id:
        selected_id = st.session_state.selected_kanban_opp_id
        
        if st.button("⬅️ Kembali ke Kanban"):
            st.session_state.selected_kanban_opp_id = None
            st.rerun()
        
        # Ambil data header
        header_row = df_kanban[df_kanban['opportunity_id'] == selected_id]
        if not header_row.empty:
            header_data = header_row.iloc[0]
            st.subheader(f"{header_data['opportunity_name']}")
            st.caption(f"Client: {header_data.get('company_name', '-')}")
            st.markdown(f"**Total Price:** Rp {format_idr(header_data['selling_price'])}")

            # Ambil Detail Item
            st.markdown("#### Solution Details")
            df_details = db.get_opportunity_details(selected_id)
            if not df_details.empty:
                if 'selling_price' in df_details.columns:
                    df_details['selling_price'] = df_details['selling_price'].apply(format_idr)
                st.dataframe(df_details, use_container_width=True)
            else:
                st.info("Tidak ada rincian item.")
        else:
            st.error("Data opportunity tidak ditemukan di list.")

    # --- Kanban Board Logic ---
    else:
        # Filter Dataframe per Stage
        open_opps = df_kanban[df_kanban['stage'] == 'Open']
        won_opps = df_kanban[df_kanban['stage'] == 'Closed Won']
        lost_opps = df_kanban[df_kanban['stage'] == 'Closed Lost']

        # Render Kolom
        c1, c2, c3 = st.columns(3)

        def render_card(row, color):
            with st.container(border=True):
                st.markdown(f"**{row['opportunity_name']}**")
                st.caption(f"🏢 {row.get('company_name', '-')}")
                st.caption(f"👤 {row['sales_name']}")
                st.markdown(f"💰 **Rp {format_idr(row['selling_price'])}**")
                
                if st.button("Lihat Detail", key=f"btn_{row['opportunity_id']}"):
                    st.session_state.selected_kanban_opp_id = row['opportunity_id']
                    st.rerun()

        with c1:
            st.markdown(f"### 🟦 Open ({len(open_opps)})")
            st.markdown(f"**Total: Rp {format_idr(open_opps['selling_price'].sum())}**")
            st.markdown("---")
            for _, row in open_opps.iterrows(): render_card(row, "blue")

        with c2:
            st.markdown(f"### 🟩 Won ({len(won_opps)})")
            st.markdown(f"**Total: Rp {format_idr(won_opps['selling_price'].sum())}**")
            st.markdown("---")
            for _, row in won_opps.iterrows(): render_card(row, "green")

        with c3:
            st.markdown(f"### 🟥 Lost ({len(lost_opps)})")
            st.markdown(f"**Total: Rp {format_idr(lost_opps['selling_price'].sum())}**")
            st.markdown("---")
            for _, row in lost_opps.iterrows(): render_card(row, "red")

@st.fragment
def tab2_dashboard(sales_group, sales_name, is_super):
    st.header("Interactive Dashboard & Search")
    
    # 1. Load Full Data (Detail Level)
    with st.spinner("Loading dataset..."):
        df = db.get_dashboard_data(sales_group, sales_name, is_super)
    
    if df.empty:
        st.info("No opportunity data available.")
        return

    # --- Pre-processing Data ---
    # A. Numerik
    for col in ['cost', 'selling_price']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # B. Tanggal (Prioritas start_date -> created_at)
    date_col = 'start_date' if 'start_date' in df.columns else 'created_at'
    if date_col in df.columns:
        df['filter_date_dt'] = pd.to_datetime(df[date_col], errors='coerce')
    
    # C. Handle NULL values (agar filter tidak error)
    fillna_cols = [
        'presales_name', 'responsible_name', 'sales_name', 
        'distributor_name', 'brand', 'pillar', 'solution', 
        'company_name', 'vertical_industry', 'stage', 
        'opportunity_name'
    ]
    for col in fillna_cols:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown").astype(str)

    # =================================================================
    # 🎛️ FILTER PANEL (SLICERS)
    # =================================================================
    with st.container(border=True):
        st.subheader("🔍 Filter Panel (Slicers)")
        
        # Helper untuk mengambil opsi unik yang sudah disortir
        def get_opts(col_name):
            return sorted(df[col_name].unique().tolist()) if col_name in df.columns else []

        # --- BARIS 1: People & Group ---
        c1, c2, c3, c4 = st.columns(4)
        with c1: sel_inputter = st.multiselect("Inputter (Presales)", get_opts('presales_name'))
        with c2: sel_pam = st.multiselect("Presales Manager (PAM)", get_opts('responsible_name'))
        with c3: sel_sales = st.multiselect("Sales Name", get_opts('sales_name'))
        with c4: sel_distributor = st.multiselect("Distributor", get_opts('distributor_name'))

        # --- BARIS 2: Product & Solution ---
        c5, c6, c7, c8 = st.columns(4)
        with c5: sel_brand = st.multiselect("Brand", get_opts('brand'))
        with c6: sel_pillar = st.multiselect("Pillar", get_opts('pillar'))
        with c7: sel_solution = st.multiselect("Solution", get_opts('solution'))
        with c8: sel_client = st.multiselect("Client / Company", get_opts('company_name'))

        # --- BARIS 3: Context & Time ---
        c9, c10, c11, c12 = st.columns(4)
        with c9: sel_vertical = st.multiselect("Vertical Industry", get_opts('vertical_industry'))
        with c10: sel_stage = st.multiselect("Stage", get_opts('stage'))
        with c11: 
            # Date Range Filter
            date_range = None
            if 'filter_date_dt' in df.columns:
                min_d = df['filter_date_dt'].min().date() if not df['filter_date_dt'].isnull().all() else None
                max_d = df['filter_date_dt'].max().date() if not df['filter_date_dt'].isnull().all() else None
                if min_d and max_d:
                    date_range = st.date_input("Start Date Range", value=(min_d, max_d))
        with c12: sel_opportunity = st.multiselect("Opportunity Name", get_opts('opportunity_name'))

    # =================================================================
    # 🔄 FILTER ENGINE
    # =================================================================
    df_filtered = df.copy()
    
    # Mapping Filter Widget ke Kolom DataFrame
    filters = {
        'presales_name': sel_inputter, 'responsible_name': sel_pam,
        'sales_name': sel_sales, 'distributor_name': sel_distributor,
        'brand': sel_brand, 'pillar': sel_pillar,
        'solution': sel_solution, 'company_name': sel_client,
        'vertical_industry': sel_vertical, 'stage': sel_stage,
        'opportunity_name': sel_opportunity
    }

    # Apply Filters Loop
    for col, selection in filters.items():
        if selection and col in df_filtered.columns:
            df_filtered = df_filtered[df_filtered[col].isin(selection)]

    # Apply Date Filter
    if isinstance(date_range, tuple) and len(date_range) == 2 and 'filter_date_dt' in df_filtered.columns:
        start_d, end_d = date_range
        mask = (df_filtered['filter_date_dt'].dt.date >= start_d) & (df_filtered['filter_date_dt'].dt.date <= end_d)
        df_filtered = df_filtered[mask]

    # =================================================================
    # 📊 SUMMARY METRICS
    # =================================================================
    st.markdown("### Summary Metrics")
    
    uniq_opps = df_filtered['opportunity_id'].nunique() if 'opportunity_id' in df_filtered.columns else 0
    uniq_cust = df_filtered['company_name'].nunique() if 'company_name' in df_filtered.columns else 0
    val_sum = df_filtered['selling_price'].sum() if 'selling_price' in df_filtered.columns else 0

    m1, m2, m3 = st.columns(3)
    m1.metric("Unique Opportunities", f"{uniq_opps}")
    m2.metric("Total Customers", f"{uniq_cust}")
    m3.metric("Total Pipeline Value", f"Rp {format_idr(val_sum)}")
    
    st.divider()

    # =================================================================
    # 📋 DATA TABLE
    # =================================================================
    st.subheader(f"Detailed Data ({len(df_filtered)} rows)")
    
    if not df_filtered.empty:
        # Pilih kolom yang relevan untuk ditampilkan
        desired_columns = [
            'opportunity_id', 'presales_name', 'sales_name', 'salesgroup_id', 
            'company_name', 'opportunity_name', 'stage', 
            'selling_price', 'pillar', 'solution', 'service', 'brand', 'pillar_product', 'solution_product'
        ]
        # Filter hanya kolom yang ada
        final_cols = [c for c in desired_columns if c in df_filtered.columns]
        
        df_display = df_filtered[final_cols].copy()
        
        # Format Selling Price di tabel
        if 'selling_price' in df_display.columns:
            df_display['selling_price'] = df_display['selling_price'].apply(format_idr)

        st.dataframe(df_display, use_container_width=True)
    else:
        st.warning("Tidak ada data yang cocok dengan kombinasi filter di atas.")

@st.fragment
def tab3_update_stage(sales_group, sales_name, is_super):
    st.header("Update Stage Process")
    st.info("Pilih stage untuk update progres opportunity.")

    # 1. Load Data Opportunity
    df_opps = db.get_kanban_data(sales_group, sales_name, is_super)
    
    if df_opps.empty:
        st.warning("Tidak ada data.")
        return

    # 2. Dropdown Pilih Opportunity
    opp_dict = {f"{row['opportunity_name']}": row['opportunity_id'] for _, row in df_opps.iterrows()}
    sorted_opp_list = sorted(opp_dict.keys())
    sel_opp = st.selectbox("Pilih Opportunity", options=sorted_opp_list, index=None)
    
    if sel_opp:
        oid = opp_dict[sel_opp]
        curr_row = df_opps[df_opps['opportunity_id'] == oid].iloc[0]
        
        # Tampilkan Info Saat Ini
        st.markdown("---")
        c1, c2 = st.columns(2)
        c1.write(f"**Current Stage:** `{curr_row['stage']}`")
        c2.write(f"**Last Note:** {curr_row.get('sales_notes', '-')}")
        
        # 3. Form Update Status
        st.subheader("Update Status")
        
        # Opsi Stage Standar
        sales_stages = [ 
            "Closed Won", "Closed Lost"
        ]
        
        # Set Default Index
        try: def_idx = sales_stages.index(curr_row['stage'])
        except: def_idx = 0
        
        new_stg = st.selectbox("New Stage", sales_stages, index=def_idx)
        
        # 4. Input Notes (Satu untuk semua kondisi)
        st.markdown("#### 📝 Stage Remarks")
        sales_notes_val = st.text_area(
            "Notes / Keterangan (Opsional)", 
            value="", 
            placeholder="Masukkan catatan terkait update stage ini...",
            height=150
        )

        # 5. Tombol Eksekusi
        if st.button("💾 Update Sales Stage", type="primary"):
            with st.spinner("Updating..."):
                # Panggil fungsi backend
                res = db.update_stage_with_notification(
                    opp_id=oid, 
                    new_stage=new_stg, 
                    notes=sales_notes_val, 
                    user_actor=sales_name
                )
                
                if res['status'] == 200:
                    # A. Pesan Sukses Statis (Kotak Hijau)
                    st.success(f"✅ BERHASIL: Opportunity telah diupdate ke {new_stg}!")
                    
                    # B. Pesan Toast (Melayang di pojok kanan atas) - Lebih modern
                    st.toast(f"Data tersimpan! Status: {new_stg}", icon="💾")
                    
                    # C. Efek Visual Tambahan
                    if new_stg == "Closed Won":
                        st.balloons()
                    elif new_stg == "Closed Lost":
                        st.error("Opportunity marked as Lost.") # Pesan merah sebentar
                    
                    # D. TAHAN RERUN (Penting!)
                    # Kita beri waktu 3 detik agar user sempat membaca pesan di atas
                    time.sleep(3)
                    
                    # E. Reset & Rerun
                    st.session_state.selected_kanban_opp_id = None
                    st.rerun()
                else:
                    st.error(res['message'])

@st.fragment
def tab4_update_price(sales_group, sales_name, is_super):
    st.header("Update Price per Item")
    st.info("💡 Edit angka pada kolom 'Selling Price' di dalam tabel secara langsung, lalu klik Simpan.")

    df_price = db.get_kanban_data(sales_group, sales_name, is_super)
    if df_price.empty:
        st.warning("Tidak ada data opportunity.")
        return

    # Dropdown Pilih Opportunity
    opp_dict_p = {f"{row['opportunity_name']}": row['opportunity_id'] for _, row in df_price.iterrows()}
    sorted_opp_list_p = sorted(opp_dict_p.keys())
    sel_opp_p = st.selectbox("Pilih Opportunity", options=sorted_opp_list_p, index=None, key="tab4_select_opp")
    
    if sel_opp_p:
        oid_p = opp_dict_p[sel_opp_p]
        header_data = db.get_sales_opportunity_header(oid_p)
        
        if header_data:
            st.markdown("---")
            c1, c2 = st.columns(2)
            c1.markdown(f"**Client:** {header_data.get('company_name')}")
            c1.markdown(f"**Stage:** {header_data.get('stage')}")
            c2.markdown(f"**Sales Rep:** {header_data.get('sales_name')}")
            c2.markdown(f"**Presales:** {header_data.get('presales_name', '-')}")
            
            # Ambil data line items
            df_items = db.get_opportunity_line_items(oid_p)
            
            if not df_items.empty:
                st.markdown("#### 📦 Rincian Item (Tabel Editor)")
                
                # Persiapkan DataFrame untuk diedit
                edit_df = df_items[['uid', 'pillar', 'solution', 'brand', 'service', 'cost', 'selling_price']].copy()
                edit_df['cost'] = pd.to_numeric(edit_df['cost'], errors='coerce').fillna(0)
                edit_df['selling_price'] = pd.to_numeric(edit_df['selling_price'], errors='coerce').fillna(0)
                
                # Render Data Editor
                edited_df = st.data_editor(
                    edit_df,
                    # Kunci semua kolom kecuali 'selling_price'
                    disabled=['uid', 'solution', 'brand', 'service', 'cost'], 
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "uid": None, # Sembunyikan UID dari layar agar rapi
                        "pillar": "Pillar",
                        "solution": "Solution",
                        "brand": "Brand",
                        "service": "Service",
                        "cost": st.column_config.NumberColumn("Cost (Modal)", format="Rp %.0f"),
                        "selling_price": st.column_config.NumberColumn(
                            "Selling Price (Edit Sini) ✏️", 
                            format="Rp %.0f", 
                            step=1000000, 
                            min_value=0
                        )
                    },
                    key=f"editor_{oid_p}"
                )
                
                # Hitung Margin Real-time berdasarkan hasil edit
                total_cost = edited_df['cost'].sum()
                total_sell = edited_df['selling_price'].sum()
                est_margin = total_sell - total_cost
                est_margin_perc = (est_margin / total_sell * 100) if total_sell > 0 else 0
                
                st.markdown("---")
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Modal (Cost)", f"Rp {format_idr(total_cost)}")
                m2.metric("Total Penawaran (Price)", f"Rp {format_idr(total_sell)}")
                
                if total_cost > 0:
                    if est_margin < 0:
                        m3.error(f"⚠️ Margin Negatif: {est_margin_perc:.1f}%")
                    else:
                        m3.success(f"✅ Margin: {est_margin_perc:.1f}%")
                
                # Deteksi perubahan & Tombol Simpan
                if st.button("💾 Simpan Perubahan Harga", type="primary", use_container_width=True):
                    changes = []
                    # Bandingkan data sebelum dan sesudah diedit
                    for i in range(len(edit_df)):
                        old_p = edit_df.iloc[i]['selling_price']
                        new_p = edited_df.iloc[i]['selling_price']
                        if old_p != new_p:
                            changes.append({
                                'uid': edited_df.iloc[i]['uid'],
                                'selling_price': new_p
                            })
                    
                    if changes:
                        with st.spinner("Menyimpan perubahan ke database..."):
                            res = db.update_line_item_prices(changes, sales_name, oid_p, header_data['opportunity_name'])
                            if res['status'] == 200:
                                st.success(f"✅ {len(changes)} item berhasil diupdate!")
                                time.sleep(1.5)
                                st.rerun()
                            else:
                                st.error(res['message'])
                    else:
                        st.info("Tidak ada perubahan angka yang terdeteksi.")
            else:
                st.warning("Belum ada item solusi yang diinput Presales.")