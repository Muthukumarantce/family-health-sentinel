import streamlit as st
import pandas as pd
import google.generativeai as genai
from ics import Calendar, Event
from datetime import datetime, date, time, timedelta
import PIL.Image
import json

# --- 1. API Configuration ---
# Ensure GEMINI_API_KEY is in your Streamlit Secrets
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # Using 'gemini-1.5-flash' for optimal speed and multimodal support
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error("API Key Configuration Error. Please check Streamlit Secrets.")

# --- 2. Helper Functions ---

def process_with_ai(uploaded_file):
    """Processes Image/PDF and returns a JSON list of medications."""
    prompt = """Analyze this medical document. 
    Extract all medications into a JSON list with these EXACT keys:
    "Tablet Name" (string), "Morning" (bool), "Afternoon" (bool), "Night" (bool), "Days" (int).
    Example: [{"Tablet Name": "Pan-D", "Morning": true, "Afternoon": false, "Night": true, "Days": 5}]
    If no meds found, return []. Return ONLY the JSON block."""
    
    try:
        doc_data = uploaded_file.getvalue()
        mime_type = uploaded_file.type
        response = model.generate_content([
            {'mime_type': mime_type, 'data': doc_data},
            prompt
        ])
        # Clean response text for JSON parsing
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except Exception as e:
        st.error(f"AI Error: {str(e)[:100]}...")
        return []

def generate_ics(df, start_date_input):
    """Safely generates an ICS file using datetime.combine to avoid TypeErrors."""
    cal = Calendar()
    
    # Convert st.date_input (date) to a base date for combine
    base_date = start_date_input if isinstance(start_date_input, date) else start_date_input.date()

    for _, row in df.iterrows():
        try:
            days = int(row.get('Days', 0))
            name = str(row.get('Tablet Name', 'Medication'))
        except:
            continue

        for day_offset in range(days):
            current_day = base_date + timedelta(days=day_offset)
            
            # Map slots (Morning: 8AM, Afternoon: 2PM, Night: 8PM)
            slots = [
                ('Morning', time(8, 0)),
                ('Afternoon', time(14, 0)),
                ('Night', time(20, 0))
            ]
            
            for slot_name, slot_time in slots:
                if row.get(slot_name):
                    event_dt = datetime.combine(current_day, slot_time)
                    event = Event(name=f"Take {name} ({slot_name})", begin=event_dt)
                    cal.events.add(event)
                    
    return cal.serialize()

# --- 3. UI Layout & State ---
st.set_page_config(page_title="Family Health Sentinel", page_icon="🏥", layout="wide")

# Initialize Session States
if "profiles" not in st.session_state:
    st.session_state.profiles = ["Amma", "Appa", "Sahasra", "Me"]
if "med_data" not in st.session_state:
    st.session_state.med_data = pd.DataFrame(columns=["Tablet Name", "Morning", "Afternoon", "Night", "Days"])

# --- Sidebar: Profile Management ---
with st.sidebar:
    st.title("🏥 Health Locker")
    active_profile = st.selectbox("👤 Select Profile", st.session_state.profiles)
    
    with st.expander("➕ Add New Profile"):
        new_name = st.text_input("Profile Name")
        if st.button("Add"):
            if new_name and new_name not in st.session_state.profiles:
                st.session_state.profiles.append(new_name)
                st.rerun()

    st.divider()
    st.info(f"Currently managing: **{active_profile}**")

# --- Main App ---
st.title("Family Health Sentinel")
st.markdown(f"**Medical Operations Hub for {active_profile}**")

tab1, tab2 = st.tabs(["🤖 AI Document Scan", "✍️ Manual Entry & Review"])

with tab1:
    col_a, col_b = st.columns([1, 1])
    with col_a:
        uploaded_file = st.file_uploader("Upload Prescription/Report (PDF/JPG)", type=['jpg', 'png', 'pdf'])
    
    with col_b:
        if uploaded_file and st.button("Analyze with Gemini AI"):
            with st.spinner("AI reading medical records..."):
                extracted_list = process_with_ai(uploaded_file)
                if extracted_list:
                    new_df = pd.DataFrame(extracted_list)
                    st.session_state.med_data = pd.concat([st.session_state.med_data, new_df], ignore_index=True)
                    st.success(f"Added {len(extracted_list)} medications to the tracker!")
                else:
                    st.warning("No medications detected. Please add manually in the next tab.")

with tab2:
    st.subheader("📋 Medication Schedule Review")
    st.caption("Edit the table below to correct AI errors or add manual entries.")
    
    # Data Editor for Hybrid Entry
    edited_df = st.data_editor(
        st.session_state.med_data,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Morning": st.column_config.CheckboxColumn(),
            "Afternoon": st.column_config.CheckboxColumn(),
            "Night": st.column_config.CheckboxColumn(),
            "Days": st.column_config.NumberColumn(min_value=1, max_value=90)
        }
    )

# --- Action: Calendar Generation ---
if not edited_df.empty:
    st.divider()
    col_c, col_d = st.columns([1, 1])
    with col_c:
        start_date = st.date_input("Course Start Date", datetime.now())
    with col_d:
        if st.button("🚀 Generate Calendar Alarms"):
            ics_content = generate_ics(edited_df, start_date)
            st.download_button(
                label="📥 Download .ics File for Phone/Calendar",
                data=ics_content,
                file_name=f"{active_profile}_meds.ics",
                mime="text/calendar"
            )
            st.balloons()
