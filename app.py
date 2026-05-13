import streamlit as st
import pandas as pd
from datetime import date
import nepali_datetime
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection

# --- SETUP & PAGE CONFIG ---
st.set_page_config(page_title="Sarangi Media House", page_icon="🎥", layout="wide")
st.title("🎥 Sarangi Media House Dashboard")

# --- DATABASE CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(worksheet="Sheet1", ttl=5)
df = df.dropna(how='all')

# Ensure all required columns exist so the app never crashes
required_cols = ['Project', 'Date', 'BS Date', 'Total', 'Advance', 'Method', 
                 'Mid Payment', 'Mid Method', 'Final Payment', 'Final Method', 
                 'Expenses', 'Type', 'Status', 'Expense Category', 'Income Category']

for col in required_cols:
    if col not in df.columns:
        df[col] = None

# Clean the data math globally
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

# Give the whole dashboard access to real dates for filtering
df['Real_Date'] = pd.to_datetime(df['Date'].apply(lambda x: str(x).split(', ')[0].split(' ')[0]), errors='coerce')

# --- TABS MENU ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Dashboard", "New Booking", "Ledger", "Add Expense", "Transfer", "🤝 Lend / Borrow", "🧾 Invoicing"
])

# --- TAB 1: DASHBOARD ---
with tab1:
    if not df.empty:
        # Ignore transfers and loans for Studio Profit
        studio_df = df[df['Type'].isin(['Shoot', 'Expense'])].copy()
        
        total_collected = studio_df["Advance"].sum() + studio_df["Mid Payment"].sum() + studio_df["Final Payment"].sum()
        total_spent = studio_df["Expenses"].sum()
        available_balance = total_collected - total_spent
        
        # Safe pending calculation (only counts actual shoots)
        total_pending = df[(df['Type'] == 'Shoot') & (df['Remaining'] > 0)]['Remaining'].sum()

        st.subheader("💰 Studio Overview")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Available Cash", f"Rs. {available_balance:,}")
        col2.metric("Pending from Clients", f"Rs. {total_pending:,}")
        col3.metric("Total Expenses", f"Rs. {total_spent:,}")

        st.divider()
        st.subheader("🏦 Where is my money?")
        
        def get_method_balance(m_name):
            adv_income = df[df['Method'].astype(str).str.strip() == m_name]['Advance'].sum()
            mid_income = df[df['Mid Method'].astype(str).str.strip() == m_name]['Mid Payment'].sum()
            fin_income = df[df['Final Method'].astype(str).str.strip() == m_name]['Final Payment'].sum()
            expense = df[df['Method'].astype(str).str.strip() == m_name]['Expenses'].sum()
            return (adv_income + mid_income + fin_income) - expense

        w1, w2, w3 = st.columns(3)
        w1.metric("Cash Drawer", f"Rs. {get_method_balance('Cash'):,}")
        w2.metric("Bank Account", f"Rs. {get_method_balance('Bank'):,}")
        w3.metric("eSewa", f"Rs. {get_method_balance('eSewa'):,}")

        # Quick Performance Tracker
        st.divider()
        st.subheader("⏱️ Quick Performance Tracker")
        time_filter = st.radio("Select Timeframe:", ["Today", "Yesterday", "Last 2 Days", "Last 7 Days", "This Month"], horizontal=True)
        today = pd.Timestamp('today').normalize()
        
        if time_filter == "Today":
            filtered_df = studio_df[studio_df['Real_Date'] == today]
        elif time_filter == "Yesterday":
            filtered_df = studio_df[studio_df['Real_Date'] == today - pd.Timedelta(days=1)]
        elif time_filter == "Last 2 Days":
            filtered_df = studio_df[studio_df['Real_Date'] >= today - pd.Timedelta(days=2)]
        elif time_filter == "Last 7 Days":
            filtered_df = studio_df[studio_df['Real_Date'] >= today - pd.Timedelta(days=7)]
        elif time_filter == "This Month":
            filtered_df = studio_df[studio_df['Real_Date'] >= today - pd.Timedelta(days=30)]
            
        t_income = filtered_df['Advance'].sum() + filtered_df['Mid Payment'].sum() + filtered_df['Final Payment'].sum()
        t_expense = filtered_df['Expenses'].sum()
        t_profit = t_income - t_expense
        
        q1, q2, q3 = st.columns(3)
        q1.metric(f"Income ({time_filter})", f"Rs. {t_income:,}")
        q2.metric(f"Expenses ({time_filter})", f"Rs. {t_expense:,}")
        q3.metric(f"Net Profit ({time_filter})", f"Rs. {t_profit:,}")

        # Upcoming Schedule
        st.divider()
        st.subheader("📅 Upcoming Shoot Schedule")
        upcoming = df[df['Type'] == "Shoot"].copy()
        upcoming = upcoming[upcoming['Real_Date'] >= today].sort_values('Real_Date')
        st.table(upcoming[['Date', 'Project', 'Status', 'Total', 'Remaining']].head(5))

        # Monthly Chart
        st.divider()
        st.subheader("📈 Monthly Cash Flow & Profit")
        chart_data = studio_df.dropna(subset=['Real_Date']).copy()
        
        if not chart_data.empty:
            chart_data['Month_Name'] = chart_data['Real_Date'].dt.strftime('%B %Y') 
            chart_data['Sort_Month'] = chart_data['Real_Date'].dt.strftime('%Y-%m') 
            chart_data['Income'] = chart_data['Advance'] + chart_data['Mid Payment'] + chart_data['Final Payment']
            
            monthly_summary = chart_data.groupby(['Sort_Month', 'Month_Name'])[['Income', 'Expenses']].sum().reset_index()
            monthly_summary = monthly_summary.sort_values('Sort_Month')
            monthly_summary['Net Profit'] = monthly_summary['Income'] - monthly_summary['Expenses']
            
            all_months = monthly_summary['Month_Name'].tolist()
            selected_months = st.multiselect("📅 Select Months to View", options=all_months, default=all_months[-6:] if len(all_months) > 6 else all_months)
            
            if selected_months:
                f_data = monthly_summary[monthly_summary['Month_Name'].isin(selected_months)]
                fig = go.Figure()
                fig.add_trace(go.Bar(x=f_data['Month_Name'], y=f_data['Income'], name='Income', marker_color='#00b4d8'))
                fig.add_trace(go.Bar(x=f_data['Month_Name'], y=f_data['Expenses'], name='Expenses', marker_color='#0077b6'))
                fig.add_trace(go.Scatter(x=f_data['Month_Name'], y=f_data['Net Profit'], name='Net Profit', mode='lines+markers', line=dict(color='#ef233c', width=3, shape='spline')))
                fig.update_layout(barmode='group', hovermode="x unified", margin=dict(l=0, r=0, t=30, b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("⚠️ Please select at least one month.")
        else:
            st.info("Not enough dated entries to generate a chart yet!")
    else:
        st.info("No data yet. Start by adding a booking!")

# --- TAB 2: NEW BOOKING ---
with tab2:
    st.subheader("📝 Add New Booking")
    with st.form("booking_form", clear_on_submit=True):
        name = st.text_input("Project / Client Name")
        inc_cat = st.selectbox("Shoot Category", ["Wedding", "Commercial", "Event", "Portrait", "Music Video", "Other"])
        
        col1, col2 = st.columns(2)
        eng_date = col1.date_input("Date of Shoot")
        
        col3, col4, col5 = st.columns(3)
        total_val = col3.number_input("Total Amount", min_value=0)
        adv_val = col4.number_input("Advance Paid", min_value=0)
        method = col5.selectbox("Payment Method", ["Cash", "Bank", "eSewa"])
        
        if st.form_submit_button("Save Booking"):
            if not name:
                st.error("Please enter a Project Name!")
            else:
                nep_date_str = str(nepali_datetime.date.from_datetime_date(eng_date))
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
                st.success("Booking saved!")
                st.rerun()

# --- TAB 3: LEDGER ---
with tab3:
    st.subheader("Transaction Ledgers")
    if not df.empty:
        df_display = df.sort_values(by='Real_Date', ascending=True).drop(columns=['Real_Date'], errors='ignore')
        
        proj_tab, exp_tab, trans_tab, loan_tab = st.tabs(["📸 Projects", "💸 Expenses", "🔄 Transfers", "🤝 Loans"])
        
        with proj_tab:
            proj_df = df_display[df_display['Type'] == 'Shoot'].reset_index(drop=True)
            edited_proj = st.data_editor(
                proj_df, num_rows="dynamic", use_container_width=True, key="p_tab",
                column_config={
                    "Status": st.column_config.SelectboxColumn("Status", options=["Booked", "Shooting", "Editing", "Completed", "Delivered"]),
                    "Income Category": st.column_config.SelectboxColumn("Category", options=["Wedding", "Commercial", "Event", "Portrait", "Music Video", "Other"]),
                    "Method": st.column_config.SelectboxColumn("Adv. Method", options=["Cash", "Bank", "eSewa"]),
                    "Mid Method": st.column_config.SelectboxColumn("Mid Method", options=["Cash", "Bank", "eSewa"]),
                    "Final Method": st.column_config.SelectboxColumn("Final Method", options=["Cash", "Bank", "eSewa"])
                },
                column_order=["Project", "Income Category", "Date", "Total", "Advance", "Method", "Mid Payment", "Mid Method", "Final Payment", "Final Method", "Remaining", "Status"]
            )
            
        with exp_tab:
            exp_df = df_display[df_display['Type'] == 'Expense'].reset_index(drop=True)
            edited_exp = st.data_editor(
                exp_df, num_rows="dynamic", use_container_width=True, key="e_tab",
                column_config={
                    "Expense Category": st.column_config.SelectboxColumn("Category", options=["Gear & Tech", "Travel & Fuel", "Freelancers", "Rent & Utilities", "Marketing", "Meals", "General"])
                },
                column_order=["Date", "Expense Category", "Project", "Method", "Expenses"]
            )
            
        with trans_tab:
            trans_df = df_display[df_display['Type'] == 'Transfer'].reset_index(drop=True)
            edited_trans = st.data_editor(trans_df, num_rows="dynamic", use_container_width=True, key="t_tab")
            
        with loan_tab:
            loan_df = df_display[df_display['Type'].isin(['Lend', 'Borrow'])].reset_index(drop=True)
            edited_loans = st.data_editor(
                loan_df, num_rows="dynamic", use_container_width=True, key="l_tab",
                column_config={
                    "Type": st.column_config.SelectboxColumn("Type", options=["Lend", "Borrow"]),
                    "Status": st.column_config.SelectboxColumn("Status", options=["Pending", "Returned", "Settled"]),
                    "Method": st.column_config.SelectboxColumn("Wallet", options=["Cash", "Bank", "eSewa"])
                },
                column_order=["Date", "Type", "Project", "Total", "Method", "Status"]
            )
        
        st.divider()
        if st.button("💾 Save All Ledgers"):
            other_df = df_display[~df_display['Type'].isin(['Shoot', 'Expense', 'Transfer', 'Lend', 'Borrow'])]
            updated_master_df = pd.concat([edited_proj, edited_exp, edited_trans, edited_loans, other_df], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_master_df)
            st.cache_data.clear()
            st.success("Ledgers saved successfully!")
            st.rerun()

# --- TAB 4: ADD EXPENSE ---
with tab4:
    st.subheader("💸 Record an Expense")
    with st.form("expense_form", clear_on_submit=True):
        ex_desc = st.text_input("What is this expense for?")
        ex_amount = st.number_input("Amount Paid (NPR)", min_value=1)
        
        c1, c2, c3 = st.columns(3)
        ex_date = c1.date_input("Date Paid")
        ex_method = c2.selectbox("Paid From", ["Cash", "Bank", "eSewa"])
        ex_cat = c3.selectbox("Category", ["Gear & Tech", "Travel & Fuel", "Freelancers", "Rent & Utilities", "Marketing", "Meals", "General"])
        
        if st.form_submit_button("Save Expense"):
            if not ex_desc:
                st.error("Please enter a description!")
            else:
                new_ex = pd.DataFrame([{
                    "Project": ex_desc, "Date": str(ex_date), "BS Date": str(nepali_datetime.date.from_datetime_date(ex_date)),
                    "Total": 0, "Advance": 0, "Mid Payment": 0, "Final Payment": 0,
                    "Method": ex_method, "Mid Method": ex_method, "Final Method": ex_method,
                    "Expenses": ex_amount, "Type": "Expense", "Status": "Completed",
                    "Expense Category": ex_cat, "Income Category": "Other"
                }])
                updated_df = pd.concat([df.drop(columns=['Real_Date'], errors='ignore'), new_ex], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.cache_data.clear()
                st.success("Expense saved!")
                st.rerun()

# --- TAB 5: TRANSFER ---
with tab5:
    st.subheader("🔄 Transfer Between Wallets")
    with st.form("transfer_form", clear_on_submit=True):
        t_amount = st.number_input("Amount", min_value=1)
        c1, c2, c3 = st.columns(3)
        t_date = c1.date_input("Date")
        t_from = c2.selectbox("From", ["Cash", "Bank", "eSewa"])
        t_to = c3.selectbox("To", ["Bank", "eSewa", "Cash"])
        
        if st.form_submit_button("Transfer"):
            if t_from == t_to:
                st.error("Cannot transfer to the same wallet!")
            else:
                # Subtract from source
                trans_out = pd.DataFrame([{"Project": f"Transfer to {t_to}", "Date": str(t_date), "BS Date": str(nepali_datetime.date.from_datetime_date(t_date)), "Total": 0, "Advance": 0, "Mid Payment": 0, "Final Payment": 0, "Method": t_from, "Mid Method": t_from, "Final Method": t_from, "Expenses": t_amount, "Type": "Transfer", "Status": "Completed", "Expense Category": "Transfer", "Income Category": "Transfer"}])
                # Add to destination
                trans_in = pd.DataFrame([{"Project": f"Transfer from {t_from}", "Date": str(t_date), "BS Date": str(nepali_datetime.date.from_datetime_date(t_date)), "Total": 0, "Advance": t_amount, "Mid Payment": 0, "Final Payment": 0, "Method": t_to, "Mid Method": t_to, "Final Method": t_to, "Expenses": 0, "Type": "Transfer", "Status": "Completed", "Expense Category": "Transfer", "Income Category": "Transfer"}])
                
                updated_df = pd.concat([df.drop(columns=['Real_Date'], errors='ignore'), trans_out, trans_in], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.cache_data.clear()
                st.success("Transfer saved!")
                st.rerun()

# --- TAB 6: LEND / BORROW ---
with tab6:
    st.subheader("🤝 Lend & Borrow Money")
    st.info("💡 Money logged here will update your Wallets, but will NOT affect Studio Profit!")
    with st.form("loan_form", clear_on_submit=True):
        loan_type = st.radio("Action:", ["Lending Money (Giving OUT)", "Borrowing Money (Receiving IN)"])
        person_name = st.text_input("Person's Name")
        loan_amount = st.number_input("Amount (NPR)", min_value=1)
        
        c1, c2 = st.columns(2)
        loan_date = c1.date_input("Date")
        loan_method = c2.selectbox("Wallet Used", ["Cash", "Bank", "eSewa"])
        
        if st.form_submit_button("Save Record"):
            if not person_name:
                st.error("Please enter a name!")
            else:
                l_adv = 0 if "Lending" in loan_type else loan_amount
                l_exp = loan_amount if "Lending" in loan_type else 0
                l_tag = "Lend" if "Lending" in loan_type else "Borrow"
                    
                new_loan = pd.DataFrame([{
                    "Project": person_name, "Date": str(loan_date), "BS Date": str(nepali_datetime.date.from_datetime_date(loan_date)),
                    "Total": loan_amount, "Advance": l_adv, "Mid Payment": 0, "Final Payment": 0,
                    "Method": loan_method, "Mid Method": loan_method, "Final Method": loan_method,
                    "Expenses": l_exp, "Type": l_tag, "Status": "Pending",
                    "Expense Category": "General", "Income Category": "Other"
                }])
                
                updated_df = pd.concat([df.drop(columns=['Real_Date'], errors='ignore'), new_loan], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.cache_data.clear()
                st.success("Loan recorded!")
                st.rerun()

# --- TAB 7: INVOICING ---
with tab7:
    st.subheader("🧾 Custom Billing & Receipts")
    st.info("Select a project below to instantly generate a WhatsApp-ready invoice!")
    
    if 'Type' in df.columns:
        shoots_df = df[df['Type'] == 'Shoot'].copy()
    else:
        shoots_df = pd.DataFrame()
        
    if not shoots_df.empty:
        client_list = shoots_df['Project'].dropna().unique().tolist()
        selected_client = st.selectbox("Select Client / Project:", client_list)
        
        if selected_client:
            client_data = shoots_df[shoots_df['Project'] == selected_client].iloc[0]
            
            c_total = pd.to_numeric(client_data.get('Total', 0))
            c_adv = pd.to_numeric(client_data.get('Advance', 0))
            c_mid = pd.to_numeric(client_data.get('Mid Payment', 0))
            c_final = pd.to_numeric(client_data.get('Final Payment', 0))
            
            c_paid = c_adv + c_mid + c_final
            c_due = c_total - c_paid
            
            invoice_text = f"""=================================
🏢 SARANGI MEDIA HOUSE 🏢
=================================
Project: {selected_client}
Date: {client_data.get('Date', 'TBD')}
---------------------------------
Total Amount:    Rs. {c_total:,}

Advance Paid:    Rs. {c_adv:,}"""

            if c_mid > 0:
                invoice_text += f"\nMid Payment:     Rs. {c_mid:,}"
            if c_final > 0:
                invoice_text += f"\nFinal Payment:   Rs. {c_final:,}"
                
            invoice_text += f"""
---------------------------------
TOTAL PAID:      Rs. {c_paid:,}
REMAINING DUE:   Rs. {c_due:,}
=================================
Thank you for your business! 🙏"""

            st.text_area("📋 Copy this text and paste it into WhatsApp:", value=invoice_text, height=350)
            
            if c_due == 0:
                st.success("🎉 This project is fully paid off!")
            elif c_due < 0:
                st.warning("⚠️ Overpaid! The client paid more than the Total Amount.")
    else:
        st.warning("No projects available to bill yet.")
