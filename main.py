import streamlit as st
import google.generativeai as genai
from ics import Calendar, Event
from datetime import datetime, timedelta
import PIL.Image
import json

# 1. Setup Gemini OCR using Streamlit Secrets
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

def extract_dosages(image):
    prompt = """Analyze this prescription. Extract:
    1. Tablet Name
    2. Dosage (Morning/Afternoon/Night)
    3. Duration (Number of days)
    Return ONLY a clean JSON list: [{"name": "...", "m": true, "a": false, "n": true, "days": 5}]"""
    response = model.generate_content([prompt, image])
    # Clean the response to ensure it's valid JSON
    clean_json = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(clean_json)

def generate_ics(dosage_list, start_date):
    cal = Calendar()
    for med in dosage_list:
        for day in range(med['days']):
            current_day = start_date + timedelta(days=day)
            if med.get('m'):
                cal.events.add(Event(name=f"Take {med['name']} (Morning)", begin=current_day.replace(hour=8, minute=0)))
            if med.get('a'):
                cal.events.add(Event(name=f"Take {med['name']} (Afternoon)", begin=current_day.replace(hour=14, minute=0)))
            if med.get('n'):
                cal.events.add(Event(name=f"Take {med['name']} (Night)", begin=current_day.replace(hour=20, minute=0)))
    return cal.serialize()

# UI Layout
st.set_page_config(page_title="Family Health Sentinel", page_icon="🏥")
st.sidebar.title("👨‍👩‍👧‍👦 Family Profiles")
profile = st.sidebar.selectbox("Select Member", ["Amma", "Appa", "Sahasra", "Me"])

st.title("🏥 Family Health Sentinel")
st.info(f"Currently managing health records for: **{profile}**")

uploaded_file = st.file_uploader("📸 Upload Prescription / Lab Report", type=['jpg', 'png', 'jpeg'])

if uploaded_file:
    img = PIL.Image.open(uploaded_file)
    st.image(img, caption="Document Preview", use_container_width=True)
    
    if st.button("🔍 Process with AI"):
        with st.spinner("AI is reading dosage instructions..."):
            try:
                data = extract_dosages(img)
                st.subheader("📋 Extracted Medication Schedule")
                st.table(data)
                
                ics_data = generate_ics(data, datetime.now())
                st.download_button(
                    label="📅 Sync to Phone Calendar (Download ICS)",
                    data=ics_data,
                    file_name=f"{profile}_meds.ics",
                    mime="text/calendar"
                )
            except Exception as e:
                st.error(f"Error processing document: {e}")
