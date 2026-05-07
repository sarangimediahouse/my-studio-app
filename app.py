import nepali_datetime
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# --- APP CONFIG ---
st.set_page_config(page_title="Studio Pro + Balance", layout="wide")
st.title("📸 Studio Manager & Digital Wallet")

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
        total_collected = df["Advance"].sum()
        total_spent = df["Expenses"].sum()
        
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
        upcoming['Date'] = pd.to_datetime(upcoming['Date'])
        upcoming = upcoming[upcoming['Date'] >= pd.Timestamp(date.today())].sort_values('Date')
        st.table(upcoming[['Date', 'Project', 'Total', 'Remaining']].head(5))
    else:
        st.info("No data yet. Start by adding a booking or expense!")

# --- TAB 2: NEW BOOKING ---
# --- TAB 2: NEW BOOKING ---
with tab2:
    st.subheader("Add New Shoot & Advance")
    with st.form("shoot_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        name = c1.text_input("Client Name")
        
        # --- NEW NEPALI DATE SECTION ---
        s_date = c2.date_input("Shoot Date (AD)")
        try:
            nepali_date = nepali_datetime.date.from_datetime_date(s_date)
            c2.caption(f"🇳🇵 Auto BS Date: **{nepali_date}**")
        except:
            nepali_date = "N/A"
        # -------------------------------
        
        total_val = c1.number_input("Full Project Price (NPR)", min_value=0)
        adv_val = c2.number_input("Advance/Deposit Paid (NPR)", min_value=0)
        method = st.selectbox("Payment Method", ["eSewa", "Fonepay", "Cash", "Bank"])
        
        if st.form_submit_button("Save Booking"):
            # --- UPDATED SAVE TO GOOGLE SHEETS ---
            new_row = pd.DataFrame([{
                "Project": name, 
                "Date": str(s_date), 
                "BS Date": str(nepali_date), # Saves to the new column!
                "Total": total_val, 
                "Advance": adv_val, 
                "Method": method, 
                "Expenses": 0, 
                "Type": "Shoot"
            }])
            # -------------------------------------
            
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_df)
            st.success("Booking and Advance saved!")
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
