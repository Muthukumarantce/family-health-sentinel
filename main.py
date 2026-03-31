import streamlit as st
import google.generativeai as genai
from ics import Calendar, Event
from datetime import datetime, timedelta
import PIL.Image
import json

# 1. Setup Gemini OCR using Streamlit Secrets
# Ensure you have GEMINI_API_KEY in your Streamlit Cloud Secrets
model = genai.GenerativeModel('gemini-1.5-flash-latest')

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

def process_document(uploaded_file):
    # Try the preferred model first
    model_names = ['gemini-1.5-flash-latest', 'gemini-1.5-flash', 'gemini-2.0-flash']
    
    for m_name in model_names:
        try:
            curr_model = genai.GenerativeModel(m_name)
            doc_data = uploaded_file.getvalue()
            mime_type = uploaded_file.type
            
            response = curr_model.generate_content([
                {'mime_type': mime_type, 'data': doc_data},
                "Extract medication schedule in JSON: [{'name': '...', 'm': true, 'a': false, 'n': true, 'days': 5}]"
            ])
            
            clean_json = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_json)
        except Exception as e:
            if "404" in str(e):
                continue # Try the next model in the list
            else:
                st.error(f"AI Error: {e}")
                break
    return []

def generate_ics(dosage_list, start_date):
    cal = Calendar()
    for med in dosage_list:
        for day in range(med.get('days', 0)):
            current_day = start_date + timedelta(days=day)
            # Create events based on Morning, Afternoon, Night flags
            if med.get('m'):
                cal.events.add(Event(name=f"Take {med['name']} (Morning)", begin=current_day.replace(hour=8, minute=0)))
            if med.get('a'):
                cal.events.add(Event(name=f"Take {med['name']} (Afternoon)", begin=current_day.replace(hour=14, minute=0)))
            if med.get('n'):
                cal.events.add(Event(name=f"Take {med['name']} (Night)", begin=current_day.replace(hour=20, minute=0)))
    return cal.serialize()

# --- UI Layout ---
st.set_page_config(page_title="Family Health Sentinel", page_icon="🏥", layout="wide")

# Custom CSS for Citi-style professional look
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { background-color: #00457C; color: white; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

st.sidebar.title("👨‍👩‍👧‍👦 Family Health Locker")
profile = st.sidebar.selectbox("Active Profile", ["Usha (Mother)", "Balasubramaniyan (Father)", "Sahasra (Daughter)", "Ishu (Wife)", "Me"])
st.sidebar.divider()
st.sidebar.info("Tip: Upload a PDF lab report or a JPG prescription to generate your schedule.")

st.title("🏥 Family Health Sentinel")
st.subheader(f"Managing: {profile}")

# Multi-format uploader
uploaded_file = st.file_uploader("📸 Upload Prescription / Lab Report (JPG, PNG, or PDF)", type=['jpg', 'png', 'jpeg', 'pdf'])

if uploaded_file:
    # Display Preview
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if uploaded_file.type == "application/pdf":
            st.success("📄 PDF Document Loaded Successfully.")
            st.caption("PDFs are processed using Gemini's native multimodal vision.")
        else:
            img = PIL.Image.open(uploaded_file)
            st.image(img, caption="Document Preview", use_container_width=True)
    
    with col2:
        if st.button("🔍 Run AI Analysis"):
            with st.spinner("Processing document logic..."):
                data = process_document(uploaded_file)
                
                if data:
                    st.write("### 📋 Detected Medication Schedule")
                    st.table(data)
                    
                    ics_data = generate_ics(data, datetime.now())
                    st.download_button(
                        label="📅 Download Alarms (.ics)",
                        data=ics_data,
                        file_name=f"{profile}_med_schedule.ics",
                        mime="text/calendar",
                        help="Click to add these reminders to your Google/Phone Calendar."
                    )
                else:
                    st.warning("No clear medication schedule found. Check the document content.")

st.divider()
st.caption("Family Health Sentinel v2.0 | Built for Personal Health Operations")
