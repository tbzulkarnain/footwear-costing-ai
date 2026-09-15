import streamlit as st
from PIL import Image
import pandas as pd
import io
import json
import re
import google.generativeai as genai

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Footwear Labor Costing AI",
    page_icon="👟",
    layout="wide"
)

st.title("👟 Footwear Labor Costing (FOB) AI Engine")
st.markdown("""
Aplikasi ini memanfaatkan **Gemini Vision AI** untuk menganalisis konstruksi sepatu dari foto, 
mendeteksi fitur manufaktur, dan memetakan nilai **SAM (Standard Allowed Minutes)** berdasarkan benchmark 
*Industrial Engineering*, lalu menghitung **Labor Cost (FOB)** secara presisi menggunakan kalkulasi Python.
""")

st.sidebar.header("⚙️ Costing Parameters Setup")

# --- FETCH API KEY FROM SECRETS OR SIDEBAR INPUT ---
secret_api_key = st.secrets.get("GEMINI_API_KEY", "")

if not secret_api_key:
    api_key = st.sidebar.text_input("Gemini API Key", type="password", help="Masukkan API Key jika tidak diset di secrets.toml")
else:
    api_key = secret_api_key
    st.sidebar.success("🔑 API Key terdeteksi dari Secrets")

monthly_salary = st.sidebar.number_input("Operator Salary / Month (IDR)", value=5000000, step=250000)
fx_rate = st.sidebar.number_input("USD Exchange Rate (1 USD = IDR...)", value=16800, step=100)
monthly_minutes = st.sidebar.number_input("Effective Work Minutes / Month", value=10400, help="Standar 173.33 jam/bulan = 10.400 menit")

# Calculate CPM (Cost Per Minute)
cpm_idr = monthly_salary / monthly_minutes
cpm_usd = cpm_idr / fx_rate

st.sidebar.markdown("---")
st.sidebar.metric("CPM (IDR/min)", f"IDR {cpm_idr:.2f}")
st.sidebar.metric("CPM (USD/min)", f"${cpm_usd:.4f}")

# Two-Column Layout
col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("1. Upload Footwear Image")
    uploaded_file = st.file_uploader("Select shoe image (JPG/PNG)", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        img = Image.open(uploaded_file)
        st.image(img, caption="Shoe Preview", use_container_width=True)

with col2:
    st.subheader("2. AI Analysis & Cost Estimation")

    if uploaded_file is not None:
        if st.button("🚀 Analyze Shoe & Calculate Costing", type="primary"):
            if not api_key:
                st.error("API Key Gemini tidak ditemukan! Harap masukkan API Key pada sidebar atau set di Streamlit Secrets.")
            else:
                with st.spinner("Analyzing image using Gemini Vision AI..."):
                    try:
                        # 1. Konfigurasi SDK Gemini
                        genai.configure(api_key=api_key.strip())
                        
                        # Menggunakan model flash yang aktif
                        model = genai.GenerativeModel('gemini-1.5-flash')

                        # 2. Prompt Visual Detection
                        prompt = """
                        You are an expert Footwear Industrial Engineer & Costing Specialist.
                        Analyze the attached footwear image and output ONLY a valid raw JSON object with the following structure:

                        {
                          "shoe_type": "low-cut",
                          "upper_complexity": "medium",
                          "upper_material": "leather/mesh",
                          "second_process_detected": true,
                          "second_process_details": "screen printing",
                          "bottom_construction": "cementing",
                          "estimated_panel_count": 6
                        }

                        Allowed values:
                        - shoe_type: "low-cut", "mid-cut", "high-cut", "boot", "slip-on"
                        - upper_complexity: "simple", "medium", "complex"
                        - bottom_construction: "cementing", "vulcanized", "stitchdown", "injection"
                        """

                        # 3. Request ke Gemini AI
                        response = model.generate_content([img, prompt])
                        
                        # Ekstrak bagian JSON menggunakan regex untuk menghindari SyntaxError string
                        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                        if json_match:
                            clean_text = json_match.group(0)
                        else:
                            clean_text = response.
