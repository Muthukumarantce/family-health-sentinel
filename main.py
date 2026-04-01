import streamlit as st
import pandas as pd
from ics import Calendar, Event
from datetime import datetime, date, time, timedelta
import PIL.Image
import json
import google.generativeai as genai

# --- Initialization ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("API Key missing in Secrets.")

# --- Helper Functions ---

def generate_ics(df, start_date):
    cal = Calendar()
    
    # Ensure start_date is a date object (Streamlit date_input can return date)
    # If it's already a datetime, we convert to date for the combine function
    if isinstance(start_date, datetime):
        base_date = start_date.date()
    else:
        base_date = start_date

    for _, row in df.iterrows():
        try:
            days = int(row.get('Days', 0))
        except (ValueError, TypeError):
            continue

        for day_offset in range(days):
            current_day = base_date + timedelta(days=day_offset)
            
            # Use datetime.combine to safely add hours/minutes to a date
            if row.get('Morning'):
                morning_time = time(8, 0) # 8:00 AM
                morning_dt = datetime.combine(current_day, morning_time)
                cal.events.add(Event(name=f"Take {row['Tablet Name']} (Morning)", begin=morning_dt))
            
            if row.get('Afternoon'):
                afternoon_time = time(14, 0) # 2:00 PM
                afternoon_dt = datetime.combine(current_day, afternoon_time)
                cal.events.add(Event(name=f"Take {row['Tablet Name']} (Afternoon)", begin=afternoon_dt))
            
            if row.get('Night'):
                night_time = time(20, 0) # 8:00 PM
                night_dt = datetime.combine(current_day, night_time)
                cal.events.add(Event(name=f"Take {row['Tablet Name']} (Night)", begin=night_dt))
                
    return cal.serialize()
# --- UI Setup ---
st.set_page_config(page_title="Family Health Sentinel", layout="wide")
st.title("🏥 Family Health Sentinel")

# Sidebar for Profile
profile = st.sidebar.selectbox("Active Profile", ["Amma", "Appa", "Sahasra", "Me"])

# Main Container
tab1, tab2 = st.tabs(["🤖 AI Upload", "✍️ Manual Entry"])

# Global state for the medication list
if "med_data" not in st.session_state:
    st.session_state.med_data = pd.DataFrame(columns=["Tablet Name", "Morning", "Afternoon", "Night", "Days"])

with tab1:
    uploaded_file = st.file_uploader("Upload Prescription (Handwritten or Digital)", type=['jpg', 'png', 'pdf'])
    if uploaded_file and st.button("Run AI Analysis"):
        try:
            # AI Logic (Simplified for token efficiency)
            doc_data = uploaded_file.getvalue()
            response = model.generate_content([{'mime_type': uploaded_file.type, 'data': doc_data}, 
                "Extract medications into JSON: [{'Tablet Name': '...', 'Morning': bool, 'Afternoon': bool, 'Night': bool, 'Days': int}]"])
            
            clean_json = response.text.replace('```json', '').replace('```', '').strip()
            new_data = pd.DataFrame(json.loads(clean_json))
            st.session_state.med_data = pd.concat([st.session_state.med_data, new_data], ignore_index=True)
            st.success("AI added medications to the list below!")
        except Exception as e:
            st.warning(f"AI could not parse document: {str(e)[:100]}... Please use Manual Entry.")

with tab2:
    st.info("Edit the table below to add or correct medication details.")
    # Editable Table (The Fallback)
    edited_df = st.data_editor(
        st.session_state.med_data,
        num_rows="dynamic",
        column_config={
            "Morning": st.column_config.CheckboxColumn(),
            "Afternoon": st.column_config.CheckboxColumn(),
            "Night": st.column_config.CheckboxColumn(),
            "Days": st.column_config.NumberColumn(min_value=1, max_value=90, step=1)
        },
        key="med_editor"
    )

# --- Final Action: Calendar Sync ---
if not edited_df.empty:
    st.divider()
    st.subheader("🗓️ Finalize Schedule")
    start_date = st.date_input("When should this course start?", datetime.now())
    
    if st.button("Generate & Download Alarms"):
        ics_data = generate_ics(edited_df, start_date)
        st.download_button(
            label="📲 Download Alarms (.ics)",
            data=ics_data,
            file_name=f"{profile}_meds.ics",
            mime="text/calendar"
        )
