import streamlit as st
import pandas as pd
from datetime import date
import uuid
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
        st.image("Sarangi white logo.png", use_container_width=True) 
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

# Ensure existing columns are available. Booking ID links Sheet1 bookings
# to individual records in the separate Events worksheet.
required_cols = ['Project', 'Date', 'BS Date', 'Total', 'Advance', 'Method',
                 'Mid Payment', 'Mid Method', 'Final Payment', 'Final Method',
                 'Expenses', 'Type', 'Status', 'Expense Category',
                 'Income Category', 'Booking ID']

for col in required_cols:
    if col not in df.columns:
        df[col] = None

# Read the separate Events worksheet. Create this worksheet manually in
# Google Sheets before recording new bookings (instructions below).
EVENT_COLUMNS = [
    'Booking ID', 'Client', 'Event', 'BS Date', 'AD Date',
    'Event Order', 'Event Status'
]
events_sheet_ready = True
try:
    events_df = conn.read(worksheet="Events", ttl=5)
    events_df = events_df.dropna(how='all')
    for col in EVENT_COLUMNS:
        if col not in events_df.columns:
            events_df[col] = None
    events_df = events_df[EVENT_COLUMNS]
except Exception:
    events_sheet_ready = False
    events_df = pd.DataFrame(columns=EVENT_COLUMNS)

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

# ==========================================
# SYNCHRONIZED AD / BS EVENT DATE PICKER
# ==========================================

BS_MONTHS = [
    "Baishakh", "Jestha", "Ashadh", "Shrawan",
    "Bhadra", "Ashwin", "Kartik", "Mangsir",
    "Poush", "Magh", "Falgun", "Chaitra"
]

def _valid_bs_days(year, month):
    """Return the valid day numbers for a Nepali year/month."""
    valid = []
    for day_number in range(1, 33):
        try:
            nepali_datetime.date(year, month, day_number)
            valid.append(day_number)
        except ValueError:
            break
    return valid

def _sync_bs_from_ad(prefix):
    """When AD changes, update all BS input values before rerender."""
    ad_value = st.session_state.get(f"{prefix}_ad")
    if ad_value:
        bs_value = nepali_datetime.date.from_datetime_date(ad_value)
        st.session_state[f"{prefix}_bs_year"] = bs_value.year
        st.session_state[f"{prefix}_bs_month"] = bs_value.month
        st.session_state[f"{prefix}_bs_day"] = bs_value.day

def _sync_ad_from_bs(prefix):
    """When a BS year/month/day changes, update AD and clamp invalid days."""
    year = st.session_state[f"{prefix}_bs_year"]
    month = st.session_state[f"{prefix}_bs_month"]
    days = _valid_bs_days(year, month)

    day_key = f"{prefix}_bs_day"
    selected_day = st.session_state.get(day_key, 1)
    if selected_day not in days:
        selected_day = min(selected_day, days[-1])
        st.session_state[day_key] = selected_day

    bs_value = nepali_datetime.date(year, month, selected_day)
    st.session_state[f"{prefix}_ad"] = bs_value.to_datetime_date()

def event_date_picker(label, prefix):
    """Display both calendars and keep their selected dates synchronized."""
    ad_key = f"{prefix}_ad"
    year_key = f"{prefix}_bs_year"
    month_key = f"{prefix}_bs_month"
    day_key = f"{prefix}_bs_day"

    # Initialize state once. Do not reset it on ordinary Streamlit reruns.
    if ad_key not in st.session_state:
        st.session_state[ad_key] = date.today()

    if year_key not in st.session_state:
        initial_bs = nepali_datetime.date.from_datetime_date(
            st.session_state[ad_key]
        )
        st.session_state[year_key] = initial_bs.year
        st.session_state[month_key] = initial_bs.month
        st.session_state[day_key] = initial_bs.day

    st.markdown(f"**{label}**")
    ad_col, bs_year_col, bs_month_col, bs_day_col = st.columns([1.35, 1, 1, 0.8])

    with ad_col:
        ad_value = st.date_input(
            "English date (AD)",
            key=ad_key,
            on_change=_sync_bs_from_ad,
            args=(prefix,)
        )

    # Keep the selected BS day valid for the currently selected month.
    available_days = _valid_bs_days(
        st.session_state[year_key], st.session_state[month_key]
    )
    if st.session_state.get(day_key) not in available_days:
        st.session_state[day_key] = min(
            st.session_state.get(day_key, 1), available_days[-1]
        )

    with bs_year_col:
        st.selectbox(
            "BS Year",
            options=list(range(1975, 2101)),
            key=year_key,
            on_change=_sync_ad_from_bs,
            args=(prefix,)
        )

    with bs_month_col:
        st.selectbox(
            "BS Month",
            options=list(range(1, 13)),
            format_func=lambda month_number: BS_MONTHS[month_number - 1],
            key=month_key,
            on_change=_sync_ad_from_bs,
            args=(prefix,)
        )

    # Recalculate options after the month/year controls have been rendered.
    current_days = _valid_bs_days(
        st.session_state[year_key], st.session_state[month_key]
    )
    if st.session_state.get(day_key) not in current_days:
        st.session_state[day_key] = min(
            st.session_state.get(day_key, 1), current_days[-1]
        )

    with bs_day_col:
        st.selectbox(
            "BS Day",
            options=current_days,
            key=day_key,
            on_change=_sync_ad_from_bs,
            args=(prefix,)
        )

    final_ad = st.session_state[ad_key]
    final_bs = nepali_datetime.date(
        st.session_state[year_key],
        st.session_state[month_key],
        st.session_state[day_key]
    )
    st.caption(f"Selected: {final_ad:%Y-%m-%d} AD  |  {final_bs} BS")
    return final_ad, str(final_bs)


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
        st.subheader("📅 Upcoming Events")

        if events_sheet_ready and not events_df.empty:
            upcoming_events = events_df.copy()
            upcoming_events["Event AD Date Parsed"] = pd.to_datetime(
                upcoming_events["AD Date"], errors="coerce"
            )
            upcoming_events = upcoming_events[
                upcoming_events["Event AD Date Parsed"] >= today
            ].sort_values(["Event AD Date Parsed", "Event Order"])
            if not upcoming_events.empty:
                st.dataframe(
                    upcoming_events[["Client", "Event", "BS Date", "AD Date", "Event Status"]],
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("No upcoming events found.")
        else:
            # Show legacy bookings from Sheet1 if no event rows exist yet.
            legacy_shoots = df[df["Type"] == "Shoot"].copy()
            legacy_shoots = legacy_shoots[legacy_shoots["Real_Date"] >= today]
            legacy_shoots = legacy_shoots.sort_values("Real_Date")
            st.dataframe(
                legacy_shoots[["Project", "BS Date", "Date", "Status", "Remaining"]].head(10),
                hide_index=True,
                use_container_width=True
            )
            if not events_sheet_ready:
                st.caption("Create the Events worksheet to see each event separately.")

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
    
    # 🧠 THE LIVE MATH BRAIN (Calculates 25% instantly)
    def update_advance():
        if "studio_total_amount" in st.session_state:
            st.session_state.studio_advance_amount = int(st.session_state.studio_total_amount * 0.25)

    st.markdown("**Client Details & Money**")
    
    # Unified layout for desktop and mobile web screens
    c_layout1, c_layout2 = st.columns([2, 1])
    name = c_layout1.text_input("Main Client Name (e.g. Rahul & Priya)", key="studio_client_name")
    inc_cat = c_layout2.selectbox("Category", ["Wedding", "Commercial", "Event", "Portrait", "Music Video", "Other"], key="studio_category")
    
    c_money1, c_money2, c_money3 = st.columns(3)
    
    # The moment you type a number here, it fires 'update_advance'
    total_val = c_money1.number_input("Total Amount", min_value=0, key="studio_total_amount", on_change=update_advance)
    
    # This box automatically updates with the result
    adv_val = c_money2.number_input("Booking Advance (25%)", min_value=0, key="studio_advance_amount")
    
    method = c_money3.selectbox("Payment Method", ["Cash", "Bank", "eSewa"], key="studio_payment_method")

    st.markdown("---")
    st.markdown("**Shoot Dates & Events**")
    
    # Each event has both calendars visible and synchronized.
    e1_name = st.text_input("Event 1 Name", value="Main Shoot", key="booking_event1_name")
    e1_date, e1_bs = event_date_picker("Event 1 Date", "booking_event1")

    st.divider()
    e2_name = st.text_input("Event 2 Name (Optional)", placeholder="e.g. Haldi", key="booking_event2_name")
    e2_date, e2_bs = event_date_picker("Event 2 Date", "booking_event2")

    st.divider()
    e3_name = st.text_input("Event 3 Name (Optional)", placeholder="e.g. Mehendi", key="booking_event3_name")
    e3_date, e3_bs = event_date_picker("Event 3 Date", "booking_event3")

    st.divider()
    e4_name = st.text_input("Event 4 Name (Optional)", placeholder="e.g. Sangeet", key="booking_event4_name")
    e4_date, e4_bs = event_date_picker("Event 4 Date", "booking_event4")

    st.divider()
    e5_name = st.text_input("Event 5 Name (Optional)", placeholder="e.g. Reception", key="booking_event5_name")
    e5_date, e5_bs = event_date_picker("Event 5 Date", "booking_event5")

    if not events_sheet_ready:
        st.warning(
            "The Google Sheets worksheet 'Events' was not found or could not be read. "
            "Create a worksheet named Events with the column headings listed in "
            "the setup instructions before saving a new booking."
        )

    # Save Button (Now works perfectly outside of the form)
    if st.button("💾 Save Booking", use_container_width=True, type="primary"):
        if not name:
            st.error("Please enter a Client Name!")
        else:
            if not events_sheet_ready:
                st.error(
                    "Booking was not saved. Please create the 'Events' worksheet "
                    "in Google Sheets first, then reload this app."
                )
                st.stop()

            booking_events = [
                (e1_name, e1_date, e1_bs),
                (e2_name, e2_date, e2_bs),
                (e3_name, e3_date, e3_bs),
                (e4_name, e4_date, e4_bs),
                (e5_name, e5_date, e5_bs)
            ]
            booking_events = [
                (event_name.strip(), event_ad, event_bs)
                for event_name, event_ad, event_bs in booking_events
                if event_name and event_name.strip()
            ]

            if not booking_events:
                st.error("Please enter at least one event name.")
                st.stop()

            booking_id = st.session_state.setdefault(
                "pending_booking_id", str(uuid.uuid4())
            )
            # One client = one booking row in Sheet1.
            # All individual event names and dates are stored in Events worksheet.
            proj_name = name.strip()

            # Keep the main financial booking record in Sheet1.
            first_event_name, first_event_ad, first_event_bs = booking_events[0]
            new_row = pd.DataFrame([{
                "Booking ID": booking_id,
                "Project": proj_name,
                "Date": str(first_event_ad),
                "BS Date": first_event_bs,
                "Total": total_val, "Advance": adv_val,
                "Mid Payment": 0, "Final Payment": 0,
                "Method": method, "Mid Method": method,
                "Final Method": method, "Expenses": 0,
                "Type": "Shoot", "Status": "Booked",
                "Income Category": inc_cat,
                "Expense Category": "General"
            }])

            # Save each event as an independent row in Events.
            new_event_rows = pd.DataFrame([
                {
                    "Booking ID": booking_id,
                    "Client": name.strip(),
                    "Event": event_name,
                    "BS Date": event_bs,
                    "AD Date": str(event_ad),
                    "Event Order": order_number,
                    "Event Status": "Booked"
                }
                for order_number, (event_name, event_ad, event_bs)
                in enumerate(booking_events, start=1)
            ], columns=EVENT_COLUMNS)

            # Remove a previous partial attempt with the same ID so retrying
            # after a network error cannot create duplicate rows.
            base_df = df[
                df['Booking ID'].astype(str) != booking_id
            ].drop(columns=['Real_Date'], errors='ignore')
            base_events_df = events_df[
                events_df['Booking ID'].astype(str) != booking_id
            ]
            updated_df = pd.concat(
                [base_df, new_row], ignore_index=True
            )
            updated_events_df = pd.concat(
                [base_events_df, new_event_rows], ignore_index=True
            )

            # Google Sheets does not provide a two-worksheet transaction.
            try:
                conn.update(worksheet="Events", data=updated_events_df)
                conn.update(worksheet="Sheet1", data=updated_df)
            except Exception as save_error:
                st.error(
                    "Google Sheets could not complete the booking save. "
                    "Please check both worksheets before trying again. "
                    f"Details: {save_error}"
                )
                st.stop()

            # Clear the retry token only after both worksheet writes succeed.
            st.session_state.pop("pending_booking_id", None)

            # Clear fields from memory after successful save
            keys_to_clear = [
                "studio_client_name", "studio_total_amount",
                "studio_advance_amount", "booking_event1_name",
                "booking_event2_name", "booking_event3_name",
                "booking_event4_name", "booking_event5_name"
            ]
            for prefix in ["booking_event1", "booking_event2", "booking_event3",
                           "booking_event4", "booking_event5"]:
                keys_to_clear.extend([
                    f"{prefix}_ad", f"{prefix}_bs_year",
                    f"{prefix}_bs_month", f"{prefix}_bs_day"
                ])
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
                    
            st.cache_data.clear()
            st.success("Booking saved as a single package successfully!")
            st.rerun()


    # ==========================================
    # CLIENT BOOKING LIST: ONE CLIENT, MANY EVENTS
    # ==========================================
    st.divider()
    st.subheader("📋 Client Booking List")
    st.caption("Each client appears once. All events booked under that client are grouped together.")

    shoot_bookings = df[df["Type"] == "Shoot"].copy()
    booking_rows = []
    if not shoot_bookings.empty:
        for _, booking in shoot_bookings.iterrows():
            booking_id_value = str(booking.get("Booking ID", "") or "").strip()
            if booking_id_value and booking_id_value.lower() != "nan" and not events_df.empty:
                client_events = events_df[
                    events_df["Booking ID"].astype(str).str.strip() == booking_id_value
                ].copy()
                if not client_events.empty:
                    client_events["Event AD Date Parsed"] = pd.to_datetime(
                        client_events["AD Date"], errors="coerce"
                    )
                    client_events = client_events.sort_values(
                        ["Event AD Date Parsed", "Event Order"]
                    )
                    event_lines = [
                        f"{row['Event']} — {row['BS Date']} BS / {row['AD Date']} AD"
                        for _, row in client_events.iterrows()
                    ]
                else:
                    event_lines = [f"Main booking — {booking.get('BS Date', '')} BS / {booking.get('Date', '')} AD"]
            else:
                # Older records remain visible even though they have no Booking ID.
                event_lines = [f"Main booking — {booking.get('BS Date', '')} BS / {booking.get('Date', '')} AD"]

            paid_amount = float(booking.get("Advance", 0) or 0) + float(booking.get("Mid Payment", 0) or 0) + float(booking.get("Final Payment", 0) or 0)
            booking_rows.append({
                "Client / Booking": booking.get("Project", ""),
                "Events in this booking": "\n".join(event_lines),
                "Total (NPR)": booking.get("Total", 0),
                "Paid (NPR)": paid_amount,
                "Due (NPR)": booking.get("Total", 0) - paid_amount,
                "Booking Status": booking.get("Status", "")
            })

    if booking_rows:
        booking_list_df = pd.DataFrame(booking_rows)
        st.dataframe(
            booking_list_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Events in this booking": st.column_config.TextColumn(
                    "Events in this booking", width="large"
                ),
                "Total (NPR)": st.column_config.NumberColumn(format="Rs. %d"),
                "Paid (NPR)": st.column_config.NumberColumn(format="Rs. %d"),
                "Due (NPR)": st.column_config.NumberColumn(format="Rs. %d")
            }
        )
    else:
        st.info("No client bookings recorded yet.")

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
    
    # 🧠 THE LIVE QUOTE MATH BRAIN
    def update_quote_advance():
        if "quote_price" in st.session_state and "quote_adv_pct" in st.session_state:
            pct_str = st.session_state.quote_adv_pct
            price = st.session_state.quote_price
            
            if "50%" in pct_str: calc = price * 0.50
            elif "30%" in pct_str: calc = price * 0.30
            elif "25%" in pct_str: calc = price * 0.25
            elif "20%" in pct_str: calc = price * 0.20
            else: calc = 0
            
            st.session_state.quote_adv_amount = int(calc)

    # Unified Layout (No st.form, so math updates instantly!)
    col_q1, col_q2 = st.columns([2, 1])
    q_client = col_q1.text_input("Prospective Client Name", key="quote_client")
    q_service = col_q2.selectbox("Package / Type", ["Wedding Photography", "Cinematography Combo", "Commercial Shoot", "Music Video Production", "Custom Event"], key="quote_service")
    
    col_q3, col_q4, col_q5 = st.columns(3)
    
    # Inputs that trigger the math instantly when you type or select
    q_price = col_q3.number_input("Quoted Price (NPR)", min_value=0, key="quote_price", on_change=update_quote_advance)
    q_advance_pct = col_q4.selectbox("Required Advance %", ["25% Advance Payment", "30% Advance Payment", "50% Advance Payment", "20% Advance Payment", "No Advance Required"], key="quote_adv_pct", on_change=update_quote_advance)
    
    # Automatically populated exact NPR amount
    q_adv_amount = col_q5.number_input("Calculated Advance (NPR)", min_value=0, key="quote_adv_amount")
    
    col_q6, col_q7 = st.columns([2, 1])
    q_raw = col_q6.radio("Raw Files Policy:", ["Raw data will be provided via client drive", "Raw files are not shared (Only edited versions)"], horizontal=True, key="quote_raw")
    q_delivery = col_q7.text_input("Estimated Delivery Time", value="3 to 4 Weeks", key="quote_delivery")
    
    q_notes = st.text_area("Custom Inclusions / Notes", placeholder="e.g., 1 Lead Photographer, 1 Cinematographer, Drone included for Main Day.", key="quote_notes")

    if st.button("Generate Quotation", use_container_width=True, type="primary"):
        if not q_client:
            st.error("Please enter a prospective client name!")
        else:
            today_ad = date.today()
            today_bs = nepali_datetime.date.today()
            
            # Format advance text cleanly for the WhatsApp message
            adv_text = f"Rs. {q_adv_amount:,} ({q_advance_pct.split(' ')[0]})" if q_adv_amount > 0 else "No Advance Required"
            
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
Booking Advance:      {adv_text}
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

    # Display the quotation box if it has been generated
    if 'generated_quote' in st.session_state and st.session_state['generated_quote']:
        st.markdown("**📋 Generated Proposal (Copy text below):**")
        st.text_area("Copy Paste to WhatsApp:", value=st.session_state['generated_quote'], height=350)
