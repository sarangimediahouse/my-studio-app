import nepali_datetime
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# --- YOUR BRANDING ---
# This puts the logo in your internet browser tab
st.set_page_config(page_title="Sarangi Media House", page_icon="sarangi.png", layout="wide")

# This puts a nice big logo right on the main page!
# You can change the 'width' number to make it perfectly sized.
st.image("sarangi.png", width=200)

# You can keep your SARANGI MEDIA HOUSE text right below it
st.title("SARANGI MEDIA HOUSE")
st.write("---")

# Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Load Data
try:
    df = conn.read(worksheet="Sheet1", ttl=0)
    df = df.dropna(how="all")
except:
    # Initialize sheet with these columns if empty
    df = pd.DataFrame(columns=["Project", "Date", "Total", "Advance", "Method", "Expenses", "Type"])

# --- TAB SECTIONS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "➕ New Booking", "📜 Ledger", "💸 Add Expense", "🔄 Transfer"])

# --- TAB 1: DASHBOARD (Money Overview) ---
# --- TAB 1: DASHBOARD (Money Overview) ---
# --- TAB 1: DASHBOARD (Money Overview) ---
# --- TAB 1: DASHBOARD (Money Overview) ---
# --- TAB 1: DASHBOARD (Money Overview) ---
# --- TAB 1: DASHBOARD (Money Overview) ---
with tab1:
    if not df.empty:
        df['Advance'] = pd.to_numeric(df['Advance'], errors='coerce').fillna(0)
        final_col = 'Final Payment' if 'Final Payment' in df.columns else 'Final_Payment'
        df['Final Payment'] = pd.to_numeric(df.get(final_col, 0), errors='coerce').fillna(0)
        df['Expenses'] = pd.to_numeric(df['Expenses'], errors='coerce').fillna(0)
        df['Total'] = pd.to_numeric(df['Total'], errors='coerce').fillna(0)
        df['Remaining'] = df['Total'] - (df['Advance'] + df['Final Payment'])
        
        # --- BLANK CELL FIX ---
        if 'Final Method' not in df.columns:
            df['Final Method'] = df['Method']
        df['Final Method'] = df['Final Method'].fillna(df['Method']) # Replaces voids with real data!
        # ----------------------
        
        studio_df = df[df['Type'] != 'Transfer']
        
        total_collected = studio_df["Advance"].sum() + studio_df["Final Payment"].sum()
        total_spent = studio_df["Expenses"].sum()
        available_balance = total_collected - total_spent
        total_pending = studio_df[studio_df['Remaining'] > 0]['Remaining'].sum()

        st.subheader("💰 Studio Overview")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Available Cash", f"Rs. {available_balance:,}")
        col2.metric("Pending from Clients", f"Rs. {total_pending:,}")
        col3.metric("Total Expenses", f"Rs. {total_spent:,}")

        st.divider()
        st.subheader("🏦 Where is my money?")
        
        def get_method_balance(m_name):
            adv_income = df[df['Method'].astype(str).str.strip() == m_name]['Advance'].sum()
            fin_income = df[df['Final Method'].astype(str).str.strip() == m_name]['Final Payment'].sum()
            expense = df[df['Method'].astype(str).str.strip() == m_name]['Expenses'].sum()
            return (adv_income + fin_income) - expense

        w1, w2, w3 = st.columns(3)
        w1.metric("Cash Drawer", f"Rs. {get_method_balance('Cash'):,}")
        w2.metric("Bank Account", f"Rs. {get_method_balance('Bank'):,}")
        w3.metric("eSewa", f"Rs. {get_method_balance('eSewa'):,}")

        st.divider()
        st.subheader("📅 Upcoming Shoot Schedule")
        upcoming = df[df['Type'] == "Shoot"].copy()
        
        if 'Status' not in upcoming.columns:
            upcoming['Status'] = "Booked"
            
        upcoming['Sort_Date'] = pd.to_datetime(upcoming['Date'].apply(lambda x: str(x).split(', ')[0].split(' ')[0]), errors='coerce')
        upcoming = upcoming[upcoming['Sort_Date'] >= pd.Timestamp(date.today())].sort_values('Sort_Date')
        st.table(upcoming[['Date', 'Project', 'Status', 'Total', 'Remaining']].head(5))
    else:
        st.info("No data yet. Start by adding a booking!")

# --- TAB 2: NEW BOOKING ---
# --- TAB 2: NEW BOOKING ---
# --- TAB 2: NEW BOOKING ---
# --- TAB 2: NEW BOOKING ---
# --- TAB 2: NEW BOOKING ---
# --- TAB 2: NEW BOOKING ---
with tab2:
    st.subheader("Add New Shoot & Advance")
    with st.form("shoot_form", clear_on_submit=True):
        name = st.text_input("Client Name")
        
        # --- 5 EDITABLE EVENT OPTIONS ---
        st.write("📅 **Select up to 5 Events** (Leave date blank if not needed)")
        
        e1_col1, e1_col2 = st.columns(2)
        n1 = e1_col1.text_input("Event 1 Name", value="Main Event")
        d1 = e1_col2.date_input("Event 1 Date", value=None)
        
        e2_col1, e2_col2 = st.columns(2)
        n2 = e2_col1.text_input("Event 2 Name", value="Reception")
        d2 = e2_col2.date_input("Event 2 Date", value=None)
        
        e3_col1, e3_col2 = st.columns(2)
        n3 = e3_col1.text_input("Event 3 Name", value="Post Shoot")
        d3 = e3_col2.date_input("Event 3 Date", value=None)
        
        e4_col1, e4_col2 = st.columns(2)
        n4 = e4_col1.text_input("Event 4 Name", value="Event 4")
        d4 = e4_col2.date_input("Event 4 Date", value=None)
        
        e5_col1, e5_col2 = st.columns(2)
        n5 = e5_col1.text_input("Event 5 Name", value="Event 5")
        d5 = e5_col2.date_input("Event 5 Date", value=None)
        # --------------------------------
        
        st.divider()
        c1, c2 = st.columns(2)
        total_val = c1.number_input("Full Project Price (NPR)", min_value=0)
        adv_val = c2.number_input("Advance/Deposit Paid (NPR)", min_value=0)
        method = st.selectbox("Payment Method", ["Cash", "Bank", "eSewa"])
        
        if st.form_submit_button("Save Booking"):
            # Group the events the user actually selected
            events = [(n1, d1), (n2, d2), (n3, d3), (n4, d4), (n5, d5)]
            valid_events = [e for e in events if e[1] is not None]
            
            if len(valid_events) == 0:
                st.error("⚠️ Please select at least one shoot date!")
            else:
                eng_dates = []
                nep_dates = []
                
                for ev_name, ev_date in valid_events:
                    eng_dates.append(f"{ev_date} ({ev_name})")
                    try:
                        nep = str(nepali_datetime.date.from_datetime_date(ev_date))
                        nep_dates.append(f"{nep} ({ev_name})")
                    except:
                        pass
                
                eng_date_str = ", ".join(eng_dates)
                nep_date_str = ", ".join(nep_dates)
                
                new_row = pd.DataFrame([{
                    "Project": name, 
                    "Date": eng_date_str, 
                    "BS Date": nep_date_str, 
                    "Total": total_val, 
                    "Advance": adv_val, 
                    "Final Payment": 0,  
                    "Method": method, 
                    "Final Method": method, # <--- THIS FIXES THE BUG FOR NEW CLIENTS!
                    "Expenses": 0, 
                    "Type": "Shoot",
                    "Status": "Booked"
                }])
                
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.cache_data.clear() # <--- FLUSHES MEMORY
                st.success(f"Booking saved! 🇳🇵 BS Dates: {nep_date_str}")
                st.rerun()
# --- TAB 3: LEDGER (History) ---
# --- TAB 3: LEDGER & EDIT (History) ---
# --- TAB 3: LEDGER ---
# --- TAB 3: LEDGER ---
# --- TAB 3: LEDGER ---
# --- TAB 3: LEDGER ---
# --- TAB 3: LEDGER ---
# --- TAB 3: LEDGER ---
# --- TAB 3: LEDGER ---
# --- TAB 3: LEDGER ---
with tab3:
    st.subheader("Transaction Ledgers")
    if not df.empty:
        df['Final Payment'] = pd.to_numeric(df.get('Final Payment', 0), errors='coerce').fillna(0)
        df['Secret_Sort'] = pd.to_datetime(df['Date'].apply(lambda x: str(x).split(', ')[0].split(' ')[0]), errors='coerce')
        df = df.sort_values(by='Secret_Sort', ascending=True).drop(columns=['Secret_Sort'])
        
        # --- BLANK CELL FIX ---
        if 'Final Method' not in df.columns:
            df['Final Method'] = df['Method']
        df['Final Method'] = df['Final Method'].fillna(df['Method'])
            
        proj_tab, exp_tab, trans_tab = st.tabs(["📸 Projects", "💸 Expenses", "🔄 Transfers"])
        
        with proj_tab:
            proj_df = df[df['Type'] == 'Shoot'].reset_index(drop=True)
            edited_proj = st.data_editor(
                proj_df, 
                num_rows="dynamic", 
                use_container_width=True, 
                key="p_tab", 
                column_config={
                    "Status": st.column_config.SelectboxColumn("Status", options=["Booked", "Shooting", "Editing", "Completed", "Delivered"]),
                    "Method": st.column_config.SelectboxColumn("Adv. Method", options=["Cash", "Bank", "eSewa"]),
                    "Final Method": st.column_config.SelectboxColumn("Final Method", options=["Cash", "Bank", "eSewa"])
                },
                column_order=["Project", "Date", "Total", "Advance", "Method", "Final Payment", "Final Method", "Remaining", "Status"]
            )
            
        with exp_tab:
            exp_df = df[df['Type'] == 'Expense'].reset_index(drop=True)
            edited_exp = st.data_editor(
                exp_df, 
                num_rows="dynamic", 
                use_container_width=True, 
                key="e_tab",
                column_config={
                    "Project": "Expense Details", 
                    "Method": "Paid From (Account)"
                },
                column_order=["Date", "Project", "Method", "Expenses"] 
            )
            
        with trans_tab:
            trans_df = df[df['Type'] == 'Transfer'].reset_index(drop=True)
            edited_trans = st.data_editor(
                trans_df, 
                num_rows="dynamic", 
                use_container_width=True, 
                key="t_tab"
            )
        
        st.divider()
        
        if st.button("💾 Save All Ledgers"):
            other_df = df[~df['Type'].isin(['Shoot', 'Expense', 'Transfer'])]
            updated_master_df = pd.concat([edited_proj, edited_exp, edited_trans, other_df], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_master_df)
            
            # --- CACHE GHOST FIX ---
            st.cache_data.clear() # Forces the app to instantly read the new data!
            
            st.success("Ledgers saved successfully!")
            st.rerun()
    else:
        st.write("No transactions yet.")
# --- TAB 4: ADD EXPENSES ---
with tab4:
    st.subheader("💸 Record an Expense")
    with st.form("expense_form", clear_on_submit=True):
        
        # No more projects! Just a simple description.
        ex_desc = st.text_input("What is this expense for?", placeholder="e.g. SD Card, Studio Rent, Editing")
        ex_amount = st.number_input("Amount Paid (NPR)", min_value=1)
        
        c1, c2 = st.columns(2)
        ex_date = c1.date_input("Date Paid")
        # Here is your Cash/Bank/eSewa selector!
        ex_method = c2.selectbox("Paid From", ["Cash", "Bank", "eSewa"]) 
        
        if st.form_submit_button("Save Expense"):
            if not ex_desc:
                st.error("⚠️ Please write down what this expense was for!")
            else:
                new_ex_row = pd.DataFrame([{
                    "Project": ex_desc, # We save the description here so it doesn't leave a blank space in Google Sheets
                    "Date": str(ex_date),
                    "BS Date": str(nepali_datetime.date.from_datetime_date(ex_date)),
                    "Total": 0, "Advance": 0, "Final Payment": 0,
                    "Method": ex_method, # Saves exactly which wallet you used
                    "Expenses": ex_amount, 
                    "Type": "Expense",
                    "Status": "Completed"
                }])
                
                updated_df = pd.concat([df, new_ex_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success(f"Recorded Rs. {ex_amount} expense paid from {ex_method}!")
                st.rerun()
            # --- TAB 5: TRANSFER MONEY ---
with tab5:
    st.subheader("🔄 Transfer Money Between Accounts")
    with st.form("transfer_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        from_acc = c1.selectbox("Withdraw From", ["Bank", "eSewa", "Cash"])
        to_acc = c2.selectbox("Deposit To", ["Cash", "Bank", "eSewa"])
        
        t_amount = st.number_input("Amount to Transfer (NPR)", min_value=1)
        t_date = st.date_input("Transfer Date")
        t_desc = st.text_input("Note (e.g., ATM Withdrawal)")
        
        if st.form_submit_button("Transfer Funds"):
            if from_acc == to_acc:
                st.error("⚠️ You cannot transfer money to the same account!")
            else:
                # Row 1: The Withdrawal (Deducts from the first account)
                row_out = pd.DataFrame([{
                    "Project": f"Transfer: {from_acc} to {to_acc} ({t_desc})",
                    "Date": str(t_date),
                    "BS Date": str(nepali_datetime.date.from_datetime_date(t_date)),
                    "Total": 0, "Advance": 0, "Final Payment": 0,
                    "Method": from_acc,
                    "Expenses": t_amount,
                    "Type": "Transfer",
                    "Status": "Completed"
                }])
                
                # Row 2: The Deposit (Adds to the second account)
                row_in = pd.DataFrame([{
                    "Project": f"Transfer: {from_acc} to {to_acc} ({t_desc})",
                    "Date": str(t_date),
                    "BS Date": str(nepali_datetime.date.from_datetime_date(t_date)),
                    "Total": 0, "Advance": t_amount, "Final Payment": 0,
                    "Method": to_acc,
                    "Expenses": 0,
                    "Type": "Transfer",
                    "Status": "Completed"
                }])
                
                # Save both rows to Google Sheets
                updated_df = pd.concat([df, row_out, row_in], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success(f"Transferred Rs. {t_amount} from {from_acc} to {to_acc}!")
                st.rerun()
