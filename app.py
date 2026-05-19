import streamlit as st
import pandas as pd
from datetime import date
import nepali_datetime
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection

# --- 🧠 DEVICE DETECTION BRAIN ---
user_agent = st.context.headers.get("User-Agent", "")
is_mobile = any(x in user_agent for x in ["Mobile", "Android", "iPhone", "iPad"])

# --- SETUP & PAGE CONFIG ---
if is_mobile:
    st.set_page_config(page_title="Sarangi Mobile", page_icon="🎥")
else:
    st.set_page_config(page_title="Sarangi Studio PC", page_icon="🎥", layout="wide")

# --- LOGO & TITLE ---
col1, col2 = st.columns([2, 8])
with col1:
    try:
        st.image("sarangi.png", use_container_width=True) 
    except:
        st.write("🎥") 
with col2:
    st.title("SARANGI MEDIA HOUSE")
with col2:
    st.title("DASHBOARD")

# --- DATABASE CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(worksheet="Sheet1", ttl=5)
df = df.dropna(how='all')

# Ensure core columns exist (NO EXTRA COLUMNS NEEDED!)
required_cols = ['Project', 'Date', 'BS Date', 'Total', 'Advance', 'Method', 
                 'Mid Payment', 'Mid Method', 'Final Payment', 'Final Method', 
                 'Expenses', 'Type', 'Status', 'Expense Category', 'Income Category']

for col in required_cols:
    if col not in df.columns:
        df[col] = None

# Clean the data math
df['Advance'] = pd.to_numeric(df['Advance'], errors='coerce').fillna(0)
df['Mid Payment'] = pd.to_numeric(df['Mid Payment'], errors='coerce').fillna(0)
df['Final Payment'] = pd.to_numeric(df['Final Payment'], errors='coerce').fillna(0)
df['Expenses'] = pd.to_numeric(df['Expenses'], errors='coerce').fillna(0)
df['Total'] = pd.to_numeric(df['Total'], errors='coerce').fillna(0)
df['Remaining'] = df['Total'] - (df['Advance'] + df['Mid Payment'] + df['Final Payment'])

df['Final Method'] = df['Final Method'].fillna(df['Method'])
df['Mid Method'] = df['Mid Method'].fillna(df['Method'])
df['Expense Category'] = df['Expense Category'].fillna("General")
df['Income Category'] = df['Income Category'].fillna("Other")

df['Real_Date'] = pd.to_datetime(df['Date'].apply(lambda x: str(x).split(', ')[0].split(' ')[0]), errors='coerce')

# --- TABS MENU ---
if is_mobile:
    tab_names = ["📊 Dash", "📝 Book", "📓 Ledger", "💸 Exp", "🔄 Move", "🤝 Loan", "🧾 Bill"]
else:
    tab_names = ["📊 Dashboard", "📝 New Booking", "📓 Ledger", "💸 Expenses", "🔄 Transfers", "🤝 Lend/Borrow", "🧾 Invoicing"]

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(tab_names)

# --- TAB 1: DASHBOARD ---
with tab1:
   if not df.empty:
        # Define the exact smart wallet function first so the overview can use it
        def get_method_balance(m_name):
            adv_income = df[df['Method'].astype(str).str.strip() == m_name]['Advance'].sum()
            mid_income = df[df['Mid Method'].astype(str).str.strip() == m_name]['Mid Payment'].sum()
            fin_income = df[df['Final Method'].astype(str).str.strip() == m_name]['Final Payment'].sum()
            expense = df[df['Method'].astype(str).str.strip() == m_name]['Expenses'].sum()
            
            balance = (adv_income + mid_income + fin_income) - expense
            
            lend_returned = df[(df['Type'] == 'Lend') & (df['Status'].isin(['Returned', 'Settled'])) & (df['Final Method'].astype(str).str.strip() == m_name)]['Total'].sum()
            borrow_returned = df[(df['Type'] == 'Borrow') & (df['Status'].isin(['Returned', 'Settled'])) & (df['Final Method'].astype(str).str.strip() == m_name)]['Total'].sum()
            
            return balance + lend_returned - borrow_returned

        # Overview calculation is now the exact sum of all wallets!
        available_balance = get_method_balance('Cash') + get_method_balance('Bank') + get_method_balance('eSewa')
        total_pending = df[(df['Type'] == 'Shoot') & (df['Remaining'] > 0)]['Remaining'].sum()
        
        # Calculate total expenses safely for display
        studio_df = df[df['Type'].isin(['Shoot', 'Expense'])].copy()
        total_spent = studio_df["Expenses"].sum()

        st.subheader("💰 Studio Overview")
        if is_mobile:
            st.metric("Total Available", f"Rs. {available_balance:,}")
            c1, c2 = st.columns(2)
            c1.metric("Pending", f"Rs. {total_pending:,}")
            c2.metric("Expenses", f"Rs. {total_spent:,}")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Available Cash", f"Rs. {available_balance:,}")
            c2.metric("Pending from Clients", f"Rs. {total_pending:,}")
            c3.metric("Total Expenses", f"Rs. {total_spent:,}")

        st.divider()
        st.subheader("🏦 Wallets")
        
        def get_method_balance(m_name):
            # Base sums
            adv_income = df[df['Method'].astype(str).str.strip() == m_name]['Advance'].sum()
            mid_income = df[df['Mid Method'].astype(str).str.strip() == m_name]['Mid Payment'].sum()
            fin_income = df[df['Final Method'].astype(str).str.strip() == m_name]['Final Payment'].sum()
            expense = df[df['Method'].astype(str).str.strip() == m_name]['Expenses'].sum()
            
            balance = (adv_income + mid_income + fin_income) - expense
            
            # Smart Adjustment for RETURNED LOANS
            lend_returned = df[(df['Type'] == 'Lend') & (df['Status'].isin(['Returned', 'Settled'])) & (df['Final Method'].astype(str).str.strip() == m_name)]['Total'].sum()
            borrow_returned = df[(df['Type'] == 'Borrow') & (df['Status'].isin(['Returned', 'Settled'])) & (df['Final Method'].astype(str).str.strip() == m_name)]['Total'].sum()
            
            return balance + lend_returned - borrow_returned

        w1, w2, w3 = st.columns(3)
        w1.metric("Cash", f"Rs. {get_method_balance('Cash'):,}")
        w2.metric("Bank", f"Rs. {get_method_balance('Bank'):,}")
        w3.metric("eSewa", f"Rs. {get_method_balance('eSewa'):,}")

        st.divider()
        st.subheader("⏱️ Daily Tracker")
        time_filter = st.radio("Timeframe:", ["Today", "Yesterday", "Last 7 Days", "This Month"], horizontal=True)
        today = pd.Timestamp('today').normalize()
        
        if time_filter == "Today": filtered_df = studio_df[studio_df['Real_Date'] == today]
        elif time_filter == "Yesterday": filtered_df = studio_df[studio_df['Real_Date'] == today - pd.Timedelta(days=1)]
        elif time_filter == "Last 7 Days": filtered_df = studio_df[studio_df['Real_Date'] >= today - pd.Timedelta(days=7)]
        else: filtered_df = studio_df[studio_df['Real_Date'] >= today - pd.Timedelta(days=30)]
            
        t_income = filtered_df['Advance'].sum() + filtered_df['Mid Payment'].sum() + filtered_df['Final Payment'].sum()
        t_expense = filtered_df['Expenses'].sum()
        t_profit = t_income - t_expense
        
        q1, q2, q3 = st.columns(3)
        q1.metric("Income", f"Rs. {t_income:,}")
        q2.metric("Expenses", f"Rs. {t_expense:,}")
        q3.metric("Profit", f"Rs. {t_profit:,}")

        st.divider()
        st.subheader("📅 Upcoming Shoots")
        upcoming = df[df['Type'] == "Shoot"].copy()
        upcoming = upcoming[upcoming['Real_Date'] >= today].sort_values('Real_Date')
        upcoming = upcoming.rename(columns={"Date": "AD Date"})
        st.dataframe(upcoming[['Project', 'BS Date', 'AD Date', 'Status', 'Remaining']].head(5), hide_index=True, use_container_width=True)

        # --- 🚨 AUTOMATIC OVERDUE PAYMENT ALERTS ---
        st.divider()
        st.subheader("🚨 Overdue Balances (Action Required)")
        
        # Filter for shoots that already happened (before or equal to today) and still have a remaining balance
        past_shoots = df[(df['Type'] == 'Shoot') & (df['Real_Date'] <= today)].copy()
        overdue_df = past_shoots[past_shoots['Remaining'] > 0].sort_values('Real_Date')
        
        if not overdue_df.empty:
            st.error(f"⚠️ You have {len(overdue_df)} clients with pending final payments for past shoots!")
            
            # Format a clean table for quick viewing
            overdue_display = overdue_df.rename(columns={"Date": "AD Date"})
            st.dataframe(
                overdue_display[['Project', 'BS Date', 'AD Date', 'Total', 'Remaining']], 
                hide_index=True, 
                use_container_width=True
            )
        else:
            st.success("✅ All past shoots are fully paid up! No overdue balances.")

# --- TAB 2: NEW BOOKING (RESTORED MULTI-EVENT FEATURE) ---
with tab2:
    st.subheader("📝 New Booking")
    st.caption("Book one client and add up to 5 different shoot dates at once!")
    with st.form("booking_form", clear_on_submit=True):
        
        st.markdown("**Client Details & Money**")
        
        # This unified layout scales beautifully on both desktop and mobile web screens
        c_layout1, c_layout2 = st.columns([2, 1])
        name = c_layout1.text_input("Main Client Name (e.g. Rahul & Priya)", key="studio_client_name")
        inc_cat = c_layout2.selectbox("Category", ["Wedding", "Commercial", "Event", "Portrait", "Music Video", "Other"], key="studio_category")
        
        c_money1, c_money2, c_money3 = st.columns(3)
        total_val = c_money1.number_input("Total Amount", min_value=0, key="studio_total_amount")
        
        # 🧠 Smart Calculator: Instantly calculates 25% of the Total Amount
        auto_adv = int(total_val * 0.25)
        adv_val = c_money2.number_input("Booking Advance (25%)", min_value=0, value=auto_adv, key="studio_advance_amount")
        
        method = c_money3.selectbox("Payment Method", ["Cash", "Bank", "eSewa"], key="studio_payment_method")

        st.markdown("---")
        st.markdown("**Shoot Dates & Events**")
        
        # Event 1 (Mandatory)
        if is_mobile:
            e1_name = st.text_input("Event 1 Name", value="Main Shoot")
            e1_date = st.date_input("Event 1 Date (AD)", key="d1")
        else:
            e1_col1, e1_col2 = st.columns(2)
            e1_name = e1_col1.text_input("Event 1 Name", value="Main Shoot")
            e1_date = e1_col2.date_input("Event 1 Date (AD)", key="d1")

        # Event 2 (Optional)
        if is_mobile:
            e2_name = st.text_input("Event 2 Name (Optional)", placeholder="e.g. Haldi")
            e2_date = st.date_input("Event 2 Date (AD)", key="d2")
        else:
            e2_col1, e2_col2 = st.columns(2)
            e2_name = e2_col1.text_input("Event 2 Name (Optional)", placeholder="e.g. Haldi")
            e2_date = e2_col2.date_input("Event 2 Date (AD)", key="d2")
            
        # Event 3 (Optional)
        if is_mobile:
            e3_name = st.text_input("Event 3 Name (Optional)", placeholder="e.g. Mehendi")
            e3_date = st.date_input("Event 3 Date (AD)", key="d3")
        else:
            e3_col1, e3_col2 = st.columns(2)
            e3_name = e3_col1.text_input("Event 3 Name (Optional)", placeholder="e.g. Mehendi")
            e3_date = e3_col2.date_input("Event 3 Date (AD)", key="d3")

        # Event 4 (Optional)
        if is_mobile:
            e4_name = st.text_input("Event 4 Name (Optional)", placeholder="e.g. Sangeet")
            e4_date = st.date_input("Event 4 Date (AD)", key="d4")
        else:
            e4_col1, e4_col2 = st.columns(2)
            e4_name = e4_col1.text_input("Event 4 Name (Optional)", placeholder="e.g. Sangeet")
            e4_date = e4_col2.date_input("Event 4 Date (AD)", key="d4")

        # Event 5 (Optional)
        if is_mobile:
            e5_name = st.text_input("Event 5 Name (Optional)", placeholder="e.g. Reception")
            e5_date = st.date_input("Event 5 Date (AD)", key="d5")
        else:
            e5_col1, e5_col2 = st.columns(2)
            e5_name = e5_col1.text_input("Event 5 Name (Optional)", placeholder="e.g. Reception")
            e5_date = e5_col2.date_input("Event 5 Date (AD)", key="d5")

        if st.form_submit_button("Save Booking", use_container_width=True):
            if not name:
                st.error("Please enter a Client Name!")
            else:
                rows_to_add = []
                
                # Create Event 1 (This holds all the money)
                bs1 = str(nepali_datetime.date.from_datetime_date(e1_date))
                proj1_name = f"{name} - {e1_name}" if e1_name else name
                rows_to_add.append({
                    "Project": proj1_name, "Date": str(e1_date), "BS Date": bs1, 
                    "Total": total_val, "Advance": adv_val, "Mid Payment": 0, "Final Payment": 0,  
                    "Method": method, "Mid Method": method, "Final Method": method, 
                    "Expenses": 0, "Type": "Shoot", "Status": "Booked", 
                    "Income Category": inc_cat, "Expense Category": "General"
                })
                
                # Create Event 2
                if e2_name:
                    bs2 = str(nepali_datetime.date.from_datetime_date(e2_date))
                    rows_to_add.append({
                        "Project": f"{name} - {e2_name}", "Date": str(e2_date), "BS Date": bs2, 
                        "Total": 0, "Advance": 0, "Mid Payment": 0, "Final Payment": 0,  
                        "Method": method, "Mid Method": method, "Final Method": method, 
                        "Expenses": 0, "Type": "Shoot", "Status": "Booked", 
                        "Income Category": inc_cat, "Expense Category": "General"
                    })
                    
                # Create Event 3
                if e3_name:
                    bs3 = str(nepali_datetime.date.from_datetime_date(e3_date))
                    rows_to_add.append({
                        "Project": f"{name} - {e3_name}", "Date": str(e3_date), "BS Date": bs3, 
                        "Total": 0, "Advance": 0, "Mid Payment": 0, "Final Payment": 0,  
                        "Method": method, "Mid Method": method, "Final Method": method, 
                        "Expenses": 0, "Type": "Shoot", "Status": "Booked", 
                        "Income Category": inc_cat, "Expense Category": "General"
                    })

                # Create Event 4
                if e4_name:
                    bs4 = str(nepali_datetime.date.from_datetime_date(e4_date))
                    rows_to_add.append({
                        "Project": f"{name} - {e4_name}", "Date": str(e4_date), "BS Date": bs4, 
                        "Total": 0, "Advance": 0, "Mid Payment": 0, "Final Payment": 0,  
                        "Method": method, "Mid Method": method, "Final Method": method, 
                        "Expenses": 0, "Type": "Shoot", "Status": "Booked", 
                        "Income Category": inc_cat, "Expense Category": "General"
                    })

                # Create Event 5
                if e5_name:
                    bs5 = str(nepali_datetime.date.from_datetime_date(e5_date))
                    rows_to_add.append({
                        "Project": f"{name} - {e5_name}", "Date": str(e5_date), "BS Date": bs5, 
                        "Total": 0, "Advance": 0, "Mid Payment": 0, "Final Payment": 0,  
                        "Method": method, "Mid Method": method, "Final Method": method, 
                        "Expenses": 0, "Type": "Shoot", "Status": "Booked", 
                        "Income Category": inc_cat, "Expense Category": "General"
                    })

                new_rows_df = pd.DataFrame(rows_to_add)
                updated_df = pd.concat([df.drop(columns=['Real_Date'], errors='ignore'), new_rows_df], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.cache_data.clear()
                st.success("All events saved to calendar successfully!")
                st.rerun()

# --- TAB 3: LEDGER ---
with tab3:
    st.subheader("📓 Ledger")
    if not df.empty:
        df_display = df.sort_values(by='Real_Date', ascending=True).drop(columns=['Real_Date'], errors='ignore')
        proj_tab, exp_tab, trans_tab, loan_tab = st.tabs(["📸 Shoots", "💸 Exp", "🔄 Move", "🤝 Loan"])
        
        with proj_tab:
            proj_df = df_display[df_display['Type'] == 'Shoot'].reset_index(drop=True)
            edited_proj = st.data_editor(
                proj_df, num_rows="dynamic", use_container_width=True, key="p_tab",
                column_config={
                    "Date": "AD Date", 
                    "Status": st.column_config.SelectboxColumn(options=["Booked", "Shooting", "Editing", "Completed", "Delivered"]),
                    "Income Category": st.column_config.SelectboxColumn(options=["Wedding", "Commercial", "Event", "Portrait", "Music Video", "Other"]),
                    "Method": st.column_config.SelectboxColumn(options=["Cash", "Bank", "eSewa"]),
                    "Mid Method": st.column_config.SelectboxColumn(options=["Cash", "Bank", "eSewa"]),
                    "Final Method": st.column_config.SelectboxColumn(options=["Cash", "Bank", "eSewa"])
                },
                column_order=["Project", "BS Date", "Date", "Status", "Income Category", "Total", "Advance", "Method", "Mid Payment", "Mid Method", "Final Payment", "Final Method", "Remaining"]
            )
            
        with exp_tab:
            exp_df = df_display[df_display['Type'] == 'Expense'].reset_index(drop=True)
            edited_exp = st.data_editor(
                exp_df, num_rows="dynamic", use_container_width=True, key="e_tab",
                column_config={"Date": "AD Date", "Expense Category": st.column_config.SelectboxColumn(options=["Gear & Tech", "Travel & Fuel", "Freelancers", "Rent & Utilities", "Marketing", "Meals", "General"])},
                column_order=["BS Date", "Date", "Project", "Expenses", "Method", "Expense Category"]
            )
            
        with trans_tab:
            trans_df = df_display[df_display['Type'] == 'Transfer'].reset_index(drop=True)
            edited_trans = st.data_editor(
                trans_df, num_rows="dynamic", use_container_width=True, key="t_tab", 
                column_config={"Date": "AD Date"},
                column_order=["BS Date", "Date", "Project", "Method", "Final Method", "Expenses", "Advance"]
            )
            
        with loan_tab:
            loan_df = df_display[df_display['Type'].isin(['Lend', 'Borrow'])].reset_index(drop=True)
            edited_loans = st.data_editor(
                loan_df, num_rows="dynamic", use_container_width=True, key="l_tab",
                column_config={
                    "Date": "AD Date",
                    "Type": st.column_config.SelectboxColumn(options=["Lend", "Borrow"]),
                    "Status": st.column_config.SelectboxColumn(options=["Pending", "Returned", "Settled"]),
                    "Method": st.column_config.SelectboxColumn("Original Wallet", options=["Cash", "Bank", "eSewa"]),
                    "Final Method": st.column_config.SelectboxColumn("Return Wallet", options=["Cash", "Bank", "eSewa"])
                },
                column_order=["BS Date", "Date", "Type", "Project", "Total", "Method", "Final Method", "Status"]
            )
        
        if st.button("💾 Save All Ledgers", use_container_width=True):
            other_df = df_display[~df_display['Type'].isin(['Shoot', 'Expense', 'Transfer', 'Lend', 'Borrow'])]
            updated_master_df = pd.concat([edited_proj, edited_exp, edited_trans, edited_loans, other_df], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_master_df)
            st.cache_data.clear()
            st.success("Saved!")
            st.rerun()

# --- TAB 4: EXPENSES ---
with tab4:
    st.subheader("💸 Record Expense")
    with st.form("expense_form", clear_on_submit=True):
        if is_mobile:
            ex_desc = st.text_input("Expense For?")
            ex_amount = st.number_input("Amount (NPR)", min_value=1)
            ex_date = st.date_input("Date (AD)")
            ex_method = st.selectbox("Paid From", ["Cash", "Bank", "eSewa"])
            ex_cat = st.selectbox("Category", ["Gear", "Freelance", "Rent", "Meals", "Other"])
        else:
            c1, c2 = st.columns(2)
            ex_desc = c1.text_input("Expense For?")
            ex_amount = c2.number_input("Amount (NPR)", min_value=1)
            c3, c4 = st.columns(2)
            ex_date = c3.date_input("Date")
            ex_method = c4.selectbox("Paid From", ["Cash", "Bank", "eSewa"])
            c5 = st.columns(1)[0]
            ex_cat = c5.selectbox("Category", ["Gear", "Freelance", "Rent", "Meals", "Other"])

        if st.form_submit_button("Save Expense", use_container_width=True):
            nep_date_str = str(nepali_datetime.date.from_datetime_date(ex_date))
            new_ex = pd.DataFrame([{
                "Project": ex_desc, "Date": str(ex_date), "BS Date": nep_date_str,
                "Total": 0, "Advance": 0, "Mid Payment": 0, "Final Payment": 0,
                "Method": ex_method, "Mid Method": ex_method, "Final Method": ex_method,
                "Expenses": ex_amount, "Type": "Expense", "Status": "Completed",
                "Expense Category": ex_cat, "Income Category": "Other"
            }])
            updated_df = pd.concat([df.drop(columns=['Real_Date'], errors='ignore'), new_ex], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_df)
            st.cache_data.clear()
            st.success("Expense Recorded!")
            st.rerun()

# --- TAB 5: TRANSFER ---
with tab5:
    st.subheader("🔄 Wallet Transfer")
    with st.form("transfer_form", clear_on_submit=True):
        t_amount = st.number_input("Amount", min_value=1)
        c1, c2 = st.columns(2)
        t_from = c1.selectbox("From", ["Cash", "Bank", "eSewa"])
        t_to = c2.selectbox("To", ["Bank", "eSewa", "Cash"])
        t_date = st.date_input("Date (AD)")
        
        if st.form_submit_button("Transfer", use_container_width=True):
            if t_from == t_to: st.error("Same wallet!")
            else:
                nep_date_str = str(nepali_datetime.date.from_datetime_date(t_date))
                trans_out = pd.DataFrame([{"Project": f"To {t_to}", "Date": str(t_date), "BS Date": nep_date_str, "Total": 0, "Advance": 0, "Mid Payment": 0, "Final Payment": 0, "Method": t_from, "Mid Method": t_from, "Final Method": t_from, "Expenses": t_amount, "Type": "Transfer", "Status": "Completed", "Expense Category": "Transfer", "Income Category": "Transfer"}])
                trans_in = pd.DataFrame([{"Project": f"From {t_from}", "Date": str(t_date), "BS Date": nep_date_str, "Total": 0, "Advance": t_amount, "Mid Payment": 0, "Final Payment": 0, "Method": t_to, "Mid Method": t_to, "Final Method": t_to, "Expenses": 0, "Type": "Transfer", "Status": "Completed", "Expense Category": "Transfer", "Income Category": "Transfer"}])
                updated_df = pd.concat([df.drop(columns=['Real_Date'], errors='ignore'), trans_out, trans_in], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.cache_data.clear()
                st.success("Transfer Done!")
                st.rerun()

# --- TAB 6: LOAN ---
with tab6:
    st.subheader("🤝 Lend / Borrow")
    with st.form("loan_form", clear_on_submit=True):
        loan_type = st.radio("Action:", ["Lending (Out)", "Borrowing (In)"])
        person = st.text_input("Name")
        amount = st.number_input("Amount", min_value=1)
        method = st.selectbox("Wallet", ["Cash", "Bank", "eSewa"])
        loan_date = st.date_input("Date (AD)")
        
        if st.form_submit_button("Save Loan", use_container_width=True):
            l_adv = 0 if "Lending" in loan_type else amount
            l_exp = amount if "Lending" in loan_type else 0
            nep_date_str = str(nepali_datetime.date.from_datetime_date(loan_date))
            
            new_loan = pd.DataFrame([{"Project": person, "Date": str(loan_date), "BS Date": nep_date_str, "Total": amount, "Advance": l_adv, "Mid Payment": 0, "Final Payment": 0, "Expenses": l_exp, "Type": "Lend" if l_exp > 0 else "Borrow", "Method": method, "Mid Method": method, "Final Method": method, "Status": "Pending", "Expense Category": "General", "Income Category": "Other"}])
            updated_df = pd.concat([df.drop(columns=['Real_Date'], errors='ignore'), new_loan], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_df)
            st.cache_data.clear()
            st.success("Loan Recorded!")
            st.rerun()

# --- TAB 7: BILLING ---
with tab7:
    st.subheader("🧾 Generate Bill")
    shoots_df = df[df['Type'] == 'Shoot'].copy()
    if not shoots_df.empty:
        # Only show the MAIN shoots in the dropdown (the ones with actual Total amounts)
        main_shoots = shoots_df[pd.to_numeric(shoots_df['Total'], errors='coerce') > 0]
        if not main_shoots.empty:
            client = st.selectbox("Select Client:", main_shoots['Project'].unique())
            if client:
                data = main_shoots[main_shoots['Project'] == client].iloc[0]
                paid = data['Advance'] + data['Mid Payment'] + data['Final Payment']
                due = data['Total'] - paid
                
                # Get exact today's date for the Bill
                today_ad = date.today()
                today_bs = nepali_datetime.date.today()
                
                invoice = f"""=================================
SARANGI MEDIA HOUSE
=================================
Bill Date:  {today_bs} (BS) / {today_ad} (AD)
Shoot Date: {data['BS Date']} (BS) / {data['Date']} (AD)
---------------------------------
Project: {client}
---------------------------------
Total Amount:    Rs. {data['Total']:,}

Booking Advance (25%): Rs. {data['Advance']:,}"""

                if data['Mid Payment'] > 0:
                    invoice += f"\nPost-Shoot (25%):     Rs. {data['Mid Payment']:,}"
                if data['Final Payment'] > 0:
                    invoice += f"\nPost-Delivery (50%):  Rs. {data['Final Payment']:,}"
                    
                invoice += f"""
---------------------------------
TOTAL PAID:      Rs. {paid:,}
REMAINING DUE:   Rs. {due:,}
=================================
Thank you
SARANGI MEDIA HOUSE🙏"""
                
                st.text_area("WhatsApp Bill:", value=invoice, height=320)
        else:
            st.warning("No projects with a Total Amount to bill yet.")
    else:
        st.warning("No projects to bill yet.")

    # --- ✍️ DIGITAL QUOTATION / DEAL MEMO BUILDER ---
    st.divider()
    st.subheader("✍️ Create Deal Quotation")
    st.caption("Generate a professional quote or contract proposal for prospective clients.")
    
    with st.form("quote_form"):
        if is_mobile:
            q_client = st.text_input("Prospective Client Name")
            q_service = st.selectbox("Package / Type", ["Wedding Photography", "Cinematography Combo", "Commercial Shoot", "Music Video Production", "Custom Event"])
            q_price = st.number_input("Quoted Price (NPR)", min_value=0)
            q_advance = st.selectbox("Required Advance %", ["50% Advance Payment", "30% Advance Payment", "20% Advance Payment", "No Advance Required"])
            q_raw = st.radio("Raw Files Policy:", ["Raw data will be provided via client drive", "Raw files are not shared (Only edited versions)"], horizontal=True)
            q_delivery = st.text_input("Estimated Delivery Time", value="3 to 4 Weeks")
        else:
            col_q1, col_q2 = st.columns(2)
            q_client = col_q1.text_input("Prospective Client Name")
            q_service = col_q2.selectbox("Package / Type", ["Wedding Photography", "Cinematography Combo", "Commercial Shoot", "Music Video Production", "Custom Event"])
            
            col_q3, col_q4, col_q5 = st.columns(3)
            q_price = col_q3.number_input("Quoted Price (NPR)", min_value=0)
            q_advance = col_q4.selectbox("Required Advance %", ["50% Advance Payment", "30% Advance Payment", "20% Advance Payment", "No Advance Required"])
            q_delivery = col_q5.text_input("Estimated Delivery Time", value="3 to 4 Weeks")
            
            q_raw = st.radio("Raw Files Policy:", ["Raw data will be provided via client drive", "Raw files are not shared (Only edited versions)"], horizontal=True)

        q_notes = st.text_area("Custom Inclusions / Notes", placeholder="e.g., 1 Lead Photographer, 1 Cinematographer, Drone included for Main Day.")

        if st.form_submit_button("Generate Quotation", use_container_width=True):
            if not q_client:
                st.error("Please enter a prospective client name!")
            else:
                today_ad = date.today()
                today_bs = nepali_datetime.date.today()
                
                quote_text = f"""=================================
💼 SARANGI MEDIA HOUSE 💼
       QUOTATION / PROPOSAL
=================================
Date: {today_bs} (BS) / {today_ad} (AD)
Prepared For: {q_client}
Project Type: {q_service}
---------------------------------
💰 COMMERCIAL TERMS:
Total Package Value:  Rs. {q_price:,}
Booking Terms:        {q_advance}
---------------------------------
🛠️ SERVICE POLICIES:
Timeline:   {q_delivery} after event completion
Data:       {q_raw}"""

                if q_notes:
                    quote_text += f"\n\n📋 CUSTOM INCLUSIONS & NOTES:\n{q_notes}"

                quote_text += """\n=================================
*This proposal is valid for 15 days.*
To lock your dates, kindly confirm via advance payment.

Looking forward to working with you! 🙏
SARANGI MEDIA HOUSE"""
                
                st.session_state['generated_quote'] = quote_text

    # Display the quotation box outside the form if it has been generated
    if 'generated_quote' in st.session_state and st.session_state['generated_quote']:
        st.markdown("**📋 Generated Proposal (Copy text below):**")
        st.text_area("Copy Paste to WhatsApp:", value=st.session_state['generated_quote'], height=350)
