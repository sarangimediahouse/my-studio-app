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
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["Dashboard", "New Booking", "Ledger", "Add Expense", "Transfer", "🤝 Lend / Borrow", "🧾 Invoicing"])

# --- TAB 1: DASHBOARD (Money Overview) ---
with tab1:
    if not df.empty:
        # 1. Clean the data
       df['Advance'] = pd.to_numeric(df['Advance'], errors='coerce').fillna(0)
        df['Mid Payment'] = pd.to_numeric(df.get('Mid Payment', 0), errors='coerce').fillna(0)
        final_col = 'Final Payment' if 'Final Payment' in df.columns else 'Final_Payment'
        df['Final Payment'] = pd.to_numeric(df.get(final_col, 0), errors='coerce').fillna(0)
        df['Expenses'] = pd.to_numeric(df['Expenses'], errors='coerce').fillna(0)
        df['Total'] = pd.to_numeric(df['Total'], errors='coerce').fillna(0)
        df['Remaining'] = df['Total'] - (df['Advance'] + df['Mid Payment'] + df['Final Payment'])
        
        if 'Final Method' not in df.columns:
            df['Final Method'] = df['Method']
        df['Final Method'] = df['Final Method'].fillna(df['Method'])
        
        studio_df = df[df['Type'].isin(['Shoot', 'Expense'])].copy()
        
        # Give the whole dashboard access to real dates
        studio_df['Real_Date'] = pd.to_datetime(studio_df['Date'].apply(lambda x: str(x).split(', ')[0].split(' ')[0]), errors='coerce')
        
        total_collected = studio_df["Advance"].sum() + studio_df["Final Payment"].sum()
        total_spent = studio_df["Expenses"].sum()
        available_balance = total_collected - total_spent
        
        # Safe pending calculation
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
            mid_income = df[df.get('Mid Method', '').astype(str).str.strip() == m_name]['Mid Payment'].sum()
            fin_income = df[df['Final Method'].astype(str).str.strip() == m_name]['Final Payment'].sum()
            expense = df[df['Method'].astype(str).str.strip() == m_name]['Expenses'].sum()
            return (adv_income + mid_income + fin_income) - expense

        w1, w2, w3 = st.columns(3)
        w1.metric("Cash Drawer", f"Rs. {get_method_balance('Cash'):,}")
        w2.metric("Bank Account", f"Rs. {get_method_balance('Bank'):,}")
        w3.metric("eSewa", f"Rs. {get_method_balance('eSewa'):,}")

        # ==========================================
        # ⏱️ NEW: QUICK TIME FILTERS
        # ==========================================
        st.divider()
        st.subheader("⏱️ Quick Performance Tracker")
        
        # Create the interactive buttons
        time_filter = st.radio(
            "Select Timeframe:", 
            ["Today", "Yesterday", "Last 2 Days", "Last 7 Days", "This Month"], 
            horizontal=True
        )
        
        # Figure out what "Today" is
        today = pd.Timestamp('today').normalize()
        
        # Filter the math based on what button you clicked
        if time_filter == "Today":
            filtered_df = studio_df[studio_df['Real_Date'] == today]
        elif time_filter == "Yesterday":
            filtered_df = studio_df[studio_df['Real_Date'] == today - pd.Timedelta(days=1)]
        elif time_filter == "Last 2 Days":
            filtered_df = studio_df[studio_df['Real_Date'] >= today - pd.Timedelta(days=2)]
        elif time_filter == "Last 7 Days":
            filtered_df = studio_df[studio_df['Real_Date'] >= today - pd.Timedelta(days=7)]
        elif time_filter == "This Month":
            # Shows everything from the last 30 days
            filtered_df = studio_df[studio_df['Real_Date'] >= today - pd.Timedelta(days=30)]
            
        t_income = filtered_df['Advance'].sum() + filtered_df['Final Payment'].sum()
        t_expense = filtered_df['Expenses'].sum()
        t_profit = t_income - t_expense
        
        # Show the quick numbers
        q1, q2, q3 = st.columns(3)
        q1.metric(f"Income ({time_filter})", f"Rs. {t_income:,}")
        q2.metric(f"Expenses ({time_filter})", f"Rs. {t_expense:,}")
        q3.metric(f"Net Profit ({time_filter})", f"Rs. {t_profit:,}")
        # ==========================================

        st.divider()
        st.subheader("📅 Upcoming Shoot Schedule")
        upcoming = df[df['Type'] == "Shoot"].copy()
        
        if 'Status' not in upcoming.columns:
            upcoming['Status'] = "Booked"
            
        upcoming['Sort_Date'] = pd.to_datetime(upcoming['Date'].apply(lambda x: str(x).split(', ')[0].split(' ')[0]), errors='coerce')
        upcoming = upcoming[upcoming['Sort_Date'] >= pd.Timestamp(date.today())].sort_values('Sort_Date')
        st.table(upcoming[['Date', 'Project', 'Status', 'Total', 'Remaining']].head(5))

        st.divider()
        st.subheader("📈 Monthly Cash Flow & Profit")
        
        chart_data = studio_df.dropna(subset=['Real_Date']).copy()
        
        if not chart_data.empty:
            chart_data['Month_Name'] = chart_data['Real_Date'].dt.strftime('%B %Y') 
            chart_data['Sort_Month'] = chart_data['Real_Date'].dt.strftime('%Y-%m') 
            chart_data['Income'] = chart_data['Advance'] + chart_data['Final Payment']
            
            monthly_summary = chart_data.groupby(['Sort_Month', 'Month_Name'])[['Income', 'Expenses']].sum().reset_index()
            monthly_summary = monthly_summary.sort_values('Sort_Month')
            monthly_summary['Net Profit'] = monthly_summary['Income'] - monthly_summary['Expenses']
            
            all_months = monthly_summary['Month_Name'].tolist()
            selected_months = st.multiselect("📅 Select Months to View", options=all_months, default=all_months[-6:] if len(all_months) > 6 else all_months)
            
            if selected_months:
                filtered_data = monthly_summary[monthly_summary['Month_Name'].isin(selected_months)]
                
                import plotly.graph_objects as go
                fig = go.Figure()
                
                fig.add_trace(go.Bar(x=filtered_data['Month_Name'], y=filtered_data['Income'], name='Income', marker_color='#00b4d8'))
                fig.add_trace(go.Bar(x=filtered_data['Month_Name'], y=filtered_data['Expenses'], name='Expenses', marker_color='#0077b6'))
                fig.add_trace(go.Scatter(x=filtered_data['Month_Name'], y=filtered_data['Net Profit'], name='Net Profit', mode='lines+markers', line=dict(color='#ef233c', width=3, shape='spline')))
                
                fig.update_layout(
                    barmode='group', 
                    hovermode="x unified", 
                    margin=dict(l=0, r=0, t=30, b=0),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("⚠️ Please select at least one month to view the chart.")
        else:
            st.info("Not enough dated entries to generate a chart yet!")

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
        
        if 'Final Method' not in df.columns:
            df['Final Method'] = df['Method']
        df['Final Method'] = df['Final Method'].fillna(df['Method'])

        if 'Expense Category' not in df.columns:
            df['Expense Category'] = "General"
        df['Expense Category'] = df['Expense Category'].fillna("General")
        
        if 'Income Category' not in df.columns:
            df['Income Category'] = "Other"
        df['Income Category'] = df['Income Category'].fillna("Other")
            
        # --- ADDED LOAN TAB HERE ---
        proj_tab, exp_tab, trans_tab, loan_tab = st.tabs(["📸 Projects", "💸 Expenses", "🔄 Transfers", "🤝 Loans"])
        
        with proj_tab:
            proj_df = df[df['Type'] == 'Shoot'].reset_index(drop=True)
            edited_proj = st.data_editor(proj_df, num_rows="dynamic", use_container_width=True, key="p_tab")
            
        with exp_tab:
            exp_df = df[df['Type'] == 'Expense'].reset_index(drop=True)
            edited_exp = st.data_editor(exp_df, num_rows="dynamic", use_container_width=True, key="e_tab")
            
        with trans_tab:
            trans_df = df[df['Type'] == 'Transfer'].reset_index(drop=True)
            edited_trans = st.data_editor(trans_df, num_rows="dynamic", use_container_width=True, key="t_tab")
            
        # --- NEW LOANS LEDGER ---
        with loan_tab:
            loan_df = df[df['Type'].isin(['Lend', 'Borrow'])].reset_index(drop=True)
            edited_loans = st.data_editor(
                loan_df, 
                num_rows="dynamic", 
                use_container_width=True, 
                key="l_tab",
                column_config={
                    "Status": st.column_config.SelectboxColumn("Status", options=["Booked", "Shooting", "Editing", "Completed", "Delivered"]),
                    "Income Category": st.column_config.SelectboxColumn("Category", options=["Wedding", "Commercial", "Event", "Portrait", "Music Video", "Other"]),
                    "Method": st.column_config.SelectboxColumn("Adv. Method", options=["Cash", "Bank", "eSewa"]),
                    "Mid Method": st.column_config.SelectboxColumn("Mid Method", options=["Cash", "Bank", "eSewa"]),
                    "Final Method": st.column_config.SelectboxColumn("Final Method", options=["Cash", "Bank", "eSewa"])
                },
                column_order=["Project", "Income Category", "Date", "Total", "Advance", "Method", "Mid Payment", "Mid Method", "Final Payment", "Final Method", "Remaining", "Status"]
        
        st.divider()
        
        if st.button("💾 Save All Ledgers"):
            # Update to save the loans too!
            other_df = df[~df['Type'].isin(['Shoot', 'Expense', 'Transfer', 'Lend', 'Borrow'])]
            updated_master_df = pd.concat([edited_proj, edited_exp, edited_trans, edited_loans, other_df], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_master_df)
            st.cache_data.clear()
            st.success("Ledgers saved successfully!")
            st.rerun()
    else:
        st.write("No transactions yet.")
# --- TAB 4: ADD EXPENSES ---
# --- TAB 4: ADD EXPENSES ---
with tab4:
    st.subheader("💸 Record an Expense")
    with st.form("expense_form", clear_on_submit=True):
        
        ex_desc = st.text_input("What is this expense for?", placeholder="e.g. SD Card, Studio Rent, Editing")
        ex_amount = st.number_input("Amount Paid (NPR)", min_value=1)
        
        c1, c2, c3 = st.columns(3)
        ex_date = c1.date_input("Date Paid")
        ex_method = c2.selectbox("Paid From", ["Cash", "Bank", "eSewa"]) 
        # --- NEW CATEGORY DROPDOWN ---
        ex_cat = c3.selectbox("Category", ["Gear & Tech", "Travel & Fuel", "Freelancers", "Rent & Utilities", "Marketing", "Meals", "General"])
        
        if st.form_submit_button("Save Expense"):
            if not ex_desc:
                st.error("⚠️ Please write down what this expense was for!")
            else:
                new_ex_row = pd.DataFrame([{
                    "Project": ex_desc, 
                    "Date": str(ex_date),
                    "BS Date": str(nepali_datetime.date.from_datetime_date(ex_date)),
                    "Total": 0, "Advance": 0, "Final Payment": 0,
                    "Method": ex_method, 
                    "Final Method": ex_method,
                    "Expenses": ex_amount, 
                    "Type": "Expense",
                    "Status": "Completed",
                    "Expense Category": ex_cat # Saves the new category!
                }])
                
                updated_df = pd.concat([df, new_ex_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.cache_data.clear() # Flushes memory instantly!
                st.success(f"Recorded Rs. {ex_amount} expense for {ex_cat}!")
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
# --- TAB 6: LEND & BORROW ---
with tab6:
    st.subheader("🤝 Lend & Borrow Money")
    st.info("💡 Money logged here will update your Wallet balances, but will NOT affect your Studio Profit charts!")
    
    with st.form("loan_form", clear_on_submit=True):
        loan_type = st.radio("What are you doing?", ["Lending Money (Giving OUT to a friend)", "Borrowing Money (Receiving IN from a friend)"])
        person_name = st.text_input("Who is this with?", placeholder="Friend's Name")
        loan_amount = st.number_input("Amount (NPR)", min_value=1)
        
        c1, c2 = st.columns(2)
        loan_date = c1.date_input("Date")
        loan_method = c2.selectbox("Wallet Used", ["Cash", "Bank", "eSewa"])
        
        if st.form_submit_button("Save Record"):
            if not person_name:
                st.error("⚠️ Please enter a name!")
            else:
                if "Lending" in loan_type:
                    # Giving money out (subtracts from wallet)
                    l_adv = 0
                    l_exp = loan_amount
                    l_tag = "Lend"
                else:
                    # Receiving money in (adds to wallet)
                    l_adv = loan_amount
                    l_exp = 0
                    l_tag = "Borrow"
                    
                new_loan = pd.DataFrame([{
                    "Project": person_name, 
                    "Date": str(loan_date),
                    "BS Date": str(nepali_datetime.date.from_datetime_date(loan_date)),
                    "Total": loan_amount, 
                    "Advance": l_adv, 
                    "Final Payment": 0,
                    "Method": loan_method, 
                    "Final Method": loan_method,
                    "Expenses": l_exp, 
                    "Type": l_tag,
                    "Status": "Pending",
                    "Expense Category": "General",
                    "Income Category": "Other"
                }])
                
                updated_df = pd.concat([df, new_loan], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.cache_data.clear()
                st.success(f"Recorded! Your {loan_method} wallet balance has been updated.")
                st.rerun()
                # --- TAB 7: INVOICE & BILLING ---
with tab7:
    st.subheader("🧾 Custom Billing & Receipts")
    st.info("Select a project below to instantly generate a WhatsApp-ready invoice!")
    
    # Only get actual shoots
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
            
            # Format the text invoice
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

            st.text_area("📋 Copy this text and paste it into WhatsApp/Email:", value=invoice_text, height=350)
            
            if c_due == 0:
                st.success("🎉 This project is fully paid off!")
            elif c_due < 0:
                st.warning("⚠️ Overpaid! The client paid more than the Total Amount.")
    else:
        st.warning("No projects available to bill yet.")
