import nepali_datetime
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# --- APP CONFIG ---
st.set_page_config(page_title="Studio Pro + Balance", layout="wide")
st.title("SARANGI MEDIA HOUSE")

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
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📅 New Booking", "📜 Ledger", "💸 Log Expense"])

# --- TAB 1: DASHBOARD (Money Overview) ---
with tab1:
    if not df.empty:
        # Calculate Finance Metrics
        # --- TAB 1: DASHBOARD (Money Overview) ---
        # Fill any empty cells with 0 to prevent math crashes
        df['Advance'] = pd.to_numeric(df['Advance'], errors='coerce').fillna(0)
        df['Final Payment'] = pd.to_numeric(df.get('Final Payment', 0), errors='coerce').fillna(0)
        df['Expenses'] = pd.to_numeric(df['Expenses'], errors='coerce').fillna(0)
        df['Total'] = pd.to_numeric(df['Total'], errors='coerce').fillna(0)

        # Calculate Finance Metrics
        total_collected = df["Advance"].sum() + df["Final Payment"].sum()
        total_spent = df["Expenses"].sum()
        available_balance = total_collected - total_spent
        
        # Pending & Credit Logic
        df['Remaining'] = df['Total'] - (df['Advance'] + df['Final Payment'])
        total_pending = df[df['Remaining'] > 0]['Remaining'].sum()
        total_credit = abs(df[df['Remaining'] < 0]['Remaining'].sum())
        
        # AVAILABLE BALANCE = Money in - Money out
        available_balance = total_collected - total_spent
        
        # Pending & Credit Logic
        df['Remaining'] = df['Total'] - df['Advance']
        total_pending = df[df['Remaining'] > 0]['Remaining'].sum()
        total_credit = abs(df[df['Remaining'] < 0]['Remaining'].sum())

        # Metric Display
        col1, col2, col3 = st.columns(3)
        col1.metric("Available Balance (NPR)", f"Rs. {available_balance:,}", help="Total Cash/eSewa collected minus expenses")
        col2.metric("Pending from Clients", f"Rs. {total_pending:,}", delta_color="inverse")
        col3.metric("Client Credit", f"Rs. {total_credit:,}")

        st.divider()
        st.subheader("Upcoming Shoot Schedule")
        upcoming = df[df['Type'] == "Shoot"].copy()
        upcoming['Sort_Date'] = pd.to_datetime(upcoming['Date'].apply(lambda x: str(x).split(', ')[0].split(' ')[0]), errors='coerce')
        upcoming = upcoming[upcoming['Sort_Date'] >= pd.Timestamp(date.today())].sort_values('Sort_Date')
        st.table(upcoming[['Date', 'Project', 'Total', 'Remaining']].head(5))
    else:
        st.info("No data yet. Start by adding a booking or expense!")

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
        method = st.selectbox("Payment Method", ["eSewa", "Fonepay", "Cash", "Bank"])
        
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
                    # This creates the nice format: "2026-05-08 (Wedding)"
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
                    "Final Payment": 0,  # <--- Here is the new line safely tucked inside!
                    "Method": method, 
                    "Expenses": 0, 
                    "Type": "Shoot"
                }])
                
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success(f"Booking saved! 🇳🇵 BS Dates: {nep_date_str}")
                st.rerun()
# --- TAB 3: LEDGER (History) ---
# --- TAB 3: LEDGER & EDIT (History) ---
with tab3:
    st.subheader("Transaction History & Editor")
    if not df.empty:
        st.info("💡 You can double-click any cell below to edit it. You can also check the box on the far left of a row and press 'Delete' on your keyboard to remove a row.")
        
        # This creates the editable table
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        
        # A button to save the changes back to Google Sheets
        if st.button("💾 Save Edits to Cloud"):
            conn.update(worksheet="Sheet1", data=edited_df)
            st.success("Changes saved successfully!")
            st.rerun()
    else:
        st.write("No transactions yet.")

# --- TAB 4: LOG EXPENSE ---
with tab4:
    st.subheader("Record an Expense")
    with st.form("expense_form", clear_on_submit=True):
        ex_name = st.text_input("What did you buy? (e.g., Petrol, Rental)")
        ex_date = st.date_input("Date of Expense")
        ex_amt = st.number_input("Amount Paid (NPR)", min_value=0)
        ex_method = st.selectbox("Paid via", ["Cash", "eSewa", "Bank"])
        
        if st.form_submit_button("Record Expense"):
            # For expenses, 'Advance' is 0, 'Total' is 0, 'Expenses' is the value
            new_ex = pd.DataFrame([{"Project": ex_name, "Date": str(ex_date), "Total": 0, "Advance": 0, "Method": ex_method, "Expenses": ex_amt, "Type": "Expense"}])
            updated_df = pd.concat([df, new_ex], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_df)
            st.success("Expense deducted from balance!")
            st.rerun()
