import streamlit as st
import pandas as pd
from datetime import date
import nepali_datetime
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection

# --- 🧠 DEVICE DETECTION BRAIN ---
# This checks if the user is on a Mobile or PC
user_agent = st.context.headers.get("User-Agent", "")
is_mobile = any(x in user_agent for x in ["Mobile", "Android", "iPhone", "iPad"])

# --- SETUP & PAGE CONFIG ---
if is_mobile:
    st.set_page_config(page_title="Sarangi Mobile", page_icon="🎥")
    layout_type = "mobile"
else:
    # Keeps your PC version Wide and Professional
    st.set_page_config(page_title="Sarangi Studio PC", page_icon="🎥", layout="wide")
    layout_type = "pc"

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

# Ensure all required columns exist
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

# --- TABS MENU (Short names for Mobile, Long names for PC) ---
if is_mobile:
    tab_names = ["📊 Dash", "📝 Book", "📓 Ledger", "💸 Exp", "🔄 Move", "🤝 Loan", "🧾 Bill"]
else:
    tab_names = ["📊 Dashboard", "📝 New Booking", "📓 Ledger", "💸 Expenses", "🔄 Transfers", "🤝 Lend/Borrow", "🧾 Invoicing"]

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(tab_names)

# --- TAB 1: DASHBOARD ---
with tab1:
    if not df.empty:
        studio_df = df[df['Type'].isin(['Shoot', 'Expense'])].copy()
        total_collected = studio_df["Advance"].sum() + studio_df["Mid Payment"].sum() + studio_df["Final Payment"].sum()
        total_spent = studio_df["Expenses"].sum()
        available_balance = total_collected - total_spent
        total_pending = df[(df['Type'] == 'Shoot') & (df['Remaining'] > 0)]['Remaining'].sum()

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
            adv_income = df[df['Method'].astype(str).str.strip() == m_name]['Advance'].sum()
            mid_income = df[df['Mid Method'].astype(str).str.strip() == m_name]['Mid Payment'].sum()
            fin_income = df[df['Final Method'].astype(str).str.strip() == m_name]['Final Payment'].sum()
            expense = df[df['Method'].astype(str).str.strip() == m_name]['Expenses'].sum()
            return (adv_income + mid_income + fin_income) - expense

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
        st.dataframe(upcoming[['Project', 'BS Date', 'Status', 'Remaining']].head(5), hide_index=True, use_container_width=True)

# --- TAB 2: NEW BOOKING (HYBRID LAYOUT) ---
with tab2:
    st.subheader("📝 New Booking")
    with st.form("booking_form", clear_on_submit=True):
        if is_mobile:
            name = st.text_input("Project Name")
            inc_cat = st.selectbox("Category", ["Wedding", "Commercial", "Event", "Portrait", "Music Video", "Other"])
            eng_date = st.date_input("Date (AD)")
            bs_manual = st.text_input("BS Date Override", placeholder="e.g. 2083-03-09")
            st.divider()
            total_val = st.number_input("Total Amount", min_value=0)
            adv_val = st.number_input("Advance Paid", min_value=0)
            method = st.selectbox("Method", ["Cash", "Bank", "eSewa"])
        else:
            # PC WIDE LAYOUT
            c1, c2 = st.columns(2)
            name = c1.text_input("Project Name")
            inc_cat = c2.selectbox("Category", ["Wedding", "Commercial", "Event", "Portrait", "Music Video", "Other"])
            c3, c4 = st.columns(2)
            eng_date = c3.date_input("Date (AD)")
            bs_manual = c4.text_input("BS Date Override")
            c5, c6, c7 = st.columns(3)
            total_val = c5.number_input("Total Amount", min_value=0)
            adv_val = c6.number_input("Advance Paid", min_value=0)
            method = c7.selectbox("Method", ["Cash", "Bank", "eSewa"])

        if st.form_submit_button("Save Booking", use_container_width=True):
            nep_date_str = bs_manual if bs_manual else str(nepali_datetime.date.from_datetime_date(eng_date))
            new_row = pd.DataFrame([{
                "Project": name, "Date": str(eng_date), "BS Date": nep_date_str, 
                "Total": total_val, "Advance": adv_val, "Mid Payment": 0, "Final Payment": 0,  
                "Method": method, "Mid Method": method, "Final Method": method, 
                "Expenses": 0, "Type": "Shoot", "Status": "Booked", 
                "Income Category": inc_cat, "Expense Category": "General"
            }])
            updated_df = pd.concat([df.drop(columns=['Real_Date'], errors='ignore'), new_row], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_df)
            st.cache_data.clear()
            st.success("Booking Saved!")
            st.rerun()

# --- TAB 3: LEDGER (WIDE FOR BOTH) ---
with tab3:
    st.subheader("📓 Ledger")
    if not df.empty:
        df_display = df.sort_values(by='Real_Date', ascending=True).drop(columns=['Real_Date'], errors='ignore')
        proj_tab, exp_tab, trans_tab, loan_tab = st.tabs(["📸 Shoots", "💸 Exp", "🔄 Move", "🤝 Loan"])
        
        with proj_tab:
            proj_df = df_display[df_display['Type'] == 'Shoot'].reset_index(drop=True)
            edited_proj = st.data_editor(proj_df, num_rows="dynamic", use_container_width=True, key="p_tab")
            
        with exp_tab:
            exp_df = df_display[df_display['Type'] == 'Expense'].reset_index(drop=True)
            edited_exp = st.data_editor(exp_df, num_rows="dynamic", use_container_width=True, key="e_tab")
            
        with trans_tab:
            trans_df = df_display[df_display['Type'] == 'Transfer'].reset_index(drop=True)
            edited_trans = st.data_editor(trans_df, num_rows="dynamic", use_container_width=True, key="t_tab")
            
        with loan_tab:
            loan_df = df_display[df_display['Type'].isin(['Lend', 'Borrow'])].reset_index(drop=True)
            edited_loans = st.data_editor(loan_df, num_rows="dynamic", use_container_width=True, key="l_tab")
        
        if st.button("💾 Save All Ledgers", use_container_width=True):
            other_df = df_display[~df_display['Type'].isin(['Shoot', 'Expense', 'Transfer', 'Lend', 'Borrow'])]
            updated_master_df = pd.concat([edited_proj, edited_exp, edited_trans, edited_loans, other_df], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_master_df)
            st.cache_data.clear()
            st.success("Saved!")
            st.rerun()

# --- TAB 4: EXPENSES (HYBRID) ---
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
            c3, c4, c5 = st.columns(3)
            ex_date = c3.date_input("Date")
            ex_method = c4.selectbox("Paid From", ["Cash", "Bank", "eSewa"])
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
        if st.form_submit_button("Transfer", use_container_width=True):
            if t_from == t_to: st.error("Same wallet!")
            else:
                nep_date_str = str(nepali_datetime.date.today())
                trans_out = pd.DataFrame([{"Project": f"To {t_to}", "Date": str(date.today()), "BS Date": nep_date_str, "Total": 0, "Advance": 0, "Expenses": t_amount, "Type": "Transfer", "Method": t_from}])
                trans_in = pd.DataFrame([{"Project": f"From {t_from}", "Date": str(date.today()), "BS Date": nep_date_str, "Total": 0, "Advance": t_amount, "Expenses": 0, "Type": "Transfer", "Method": t_to}])
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
        if st.form_submit_button("Save Loan", use_container_width=True):
            l_adv = 0 if "Lending" in loan_type else amount
            l_exp = amount if "Lending" in loan_type else 0
            new_loan = pd.DataFrame([{"Project": person, "Date": str(date.today()), "BS Date": str(nepali_datetime.date.today()), "Total": amount, "Advance": l_adv, "Expenses": l_exp, "Type": "Lend" if l_exp > 0 else "Borrow", "Method": method, "Status": "Pending"}])
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
        client = st.selectbox("Select Client:", shoots_df['Project'].unique())
        if client:
            data = shoots_df[shoots_df['Project'] == client].iloc[0]
            paid = data['Advance'] + data['Mid Payment'] + data['Final Payment']
            due = data['Total'] - paid
            invoice = f"SARANGI MEDIA\nProject: {client}\nDate: {data['BS Date']}\nTotal: Rs. {data['Total']:,}\nPaid: Rs. {paid:,}\nDue: Rs. {due:,}"
            st.text_area("WhatsApp Bill:", value=invoice, height=200)
