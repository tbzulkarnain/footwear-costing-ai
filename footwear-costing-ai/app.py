import streamlit as st
from PIL import Image
import pandas as pd
import io
import requests
import base64

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Footwear Labor Costing AI",
    page_icon="👟",
    layout="wide"
)

st.title("👟 Footwear Labor Costing (FOB) AI Engine")
st.markdown("""
This application utilizes **Gemini Vision AI** to analyze footwear construction photos, 
extract manufacturing features, map estimated Industrial Engineering **SAM (Standard Allowed Minutes)**, 
and calculate **Labor Cost (FOB)** automatically.
""")

st.sidebar.header("⚙️ Costing Parameters Setup")

# --- FETCH API KEY FROM SECRETS OR SIDEBAR INPUT ---
secret_api_key = st.secrets.get("GEMINI_API_KEY", "")

# BENAR (Kunci aman tersimpan di belakang layar):
api_key_input = st.sidebar.text_input(
    "Gemini API Key (Optional)", 
    type="password", 
    help="Leave blank to use the app's default key, or enter your own Gemini API Key."
)

# Gunakan input user jika ada, jika kosong gunakan secret_api_key dari Streamlit
api_key = api_key_input if api_key_input else secret_api_key

monthly_salary = st.sidebar.number_input("Operator Salary / Month (IDR)", value=5000000, step=250000)
fx_rate = st.sidebar.number_input("USD Exchange Rate (1 USD = IDR...)", value=16800, step=100)
monthly_minutes = st.sidebar.number_input("Effective Work Minutes / Month", value=10400, help="Standard 173.33 hours/month")

# Calculate CPM (Cost Per Minute)
cpm_idr = monthly_salary / monthly_minutes
cpm_usd = cpm_idr / fx_rate

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
                st.error("Please enter your Gemini API Key in the sidebar or configure Streamlit Secrets!")
            else:
                with st.spinner("Analyzing image using Gemini AI..."):
                    try:
                        # 1. Prepare Image to Base64
                        img_byte_arr = io.BytesIO()
                        img_format = img.format if img.format else 'JPEG'
                        img.save(img_byte_arr, format=img_format)
                        img_bytes = img_byte_arr.getvalue()
                        base64_image = base64.b64encode(img_bytes).decode('utf-8')
                        
                        prompt = """
                        You are an Industrial Engineering & Costing Specialist in the footwear manufacturing industry.
                        Analyze this physical shoe photograph and provide structured output detailing:

                        1. Shoe Type (Low-cut / Mid-cut / High-cut / Boot / Slip-on)
                        2. Upper Complexity (Simple / Medium / Complex) - based on cutting panel count and stitching layers
                        3. Upper Material (Estimated: Mesh, Synthetic Leather, Genuine Leather, Knit, Canvas, etc.)
                        4. 2nd Process Detected (Yes/No: Embroidery, Screen Printing, Heat Transfer, Emboss, TPU welding, etc.)
                        5. Bottom Construction (Cementing, Vulcanized, Stitchdown, Injection, etc.)
                        6. Estimated Feature Breakdown for IE SAM Reference:
                           - Upper Cutting Panel Count: (Estimated panel count)
                           - Stitching Lines Complexity: (Low/Medium/High)
                           - Secondary Process Count: (Count of decorative/outer processes)

                        Answer directly with bullet points without formal introductory greetings.
                        """
                        
                        clean_key = api_key.strip()
                        
                        # 2. Gemini 3.6 Flash Endpoint
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={clean_key}"
                        
                        headers = {
                            "Content-Type": "application/json",
                            "x-goog-api-key": clean_key
                        }
                        
                        payload = {
                            "contents": [{
                                "parts": [
                                    {"text": prompt},
                                    {
                                        "inline_data": {
                                            "mime_type": f"image/{img_format.lower()}",
                                            "data": base64_image
                                        }
                                    }
                                ]
                            }]
                        }
                        
                        res = requests.post(url, headers=headers, json=payload)
                        res_json = res.json()
                        
                        if res.status_code != 200:
                            err_msg = res_json.get('error', {}).get('message', str(res_json))
                            raise Exception(f"API Error ({res.status_code}): {err_msg}")
                        
                        output_text = res_json['candidates'][0]['content']['parts'][0]['text']
                        ai_text = output_text.lower()
                        
                        with st.expander("📄 View AI Visual Detection Results", expanded=True):
                            st.write(output_text)
                        
                        # --- IE SAM BENCHMARK LOGIC ---
                        IE_BENCHMARK = {
                            'stitching': {
                                'base': {'low-cut': 10.0, 'high-cut': 14.0, 'slip-on': 8.0},
                                'complexity_add_on': {'simple': 0.0, 'medium': 2.5, 'complex': 5.0}
                            },
                            'assembly': {'cementing': 8.0, 'vulcanized': 9.0},
                            'second_process': {'base': 1.5}
                        }
                        
                        estimated_sam = []
                        
                        if 'low-cut' in ai_text:
                            estimated_sam.append({"Process": "Base Upper Stitching (Low-cut)", "Department": "Stitching", "SAM": IE_BENCHMARK['stitching']['base']['low-cut']})
                        elif 'high-cut' in ai_text:
                            estimated_sam.append({"Process": "Base Upper Stitching (High-cut)", "Department": "Stitching", "SAM": IE_BENCHMARK['stitching']['base']['high-cut']})
                        else:
                            estimated_sam.append({"Process": "Base Upper Stitching (Standard)", "Department": "Stitching", "SAM": 10.0})

                        if 'medium' in ai_text:
                            estimated_sam.append({"Process": "Upper Complexity Add-on (Medium)", "Department": "Stitching", "SAM": IE_BENCHMARK['stitching']['complexity_add_on']['medium']})
                        elif 'complex' in ai_text:
                            estimated_sam.append({"Process": "Upper Complexity Add-on (Complex)", "Department": "Stitching", "SAM": IE_BENCHMARK['stitching']['complexity_add_on']['complex']})

                        if 'yes' in ai_text or 'detected' in ai_text:
                            estimated_sam.append({"Process": "Secondary Process (Decorations/Logo)", "Department": "2nd Process", "SAM": IE_BENCHMARK['second_process']['base']})

                        if 'cementing' in ai_text:
                            estimated_sam.append({"Process": "Bottom Assembly & Lasting (Cementing)", "Department": "Assembly", "SAM": IE_BENCHMARK['assembly']['cementing']})
                        else:
                            estimated_sam.append({"Process": "Bottom Assembly & Lasting (Standard)", "Department": "Assembly", "SAM": 8.0})

                        # --- COST CALCULATION ---
                        DEPT_SETTINGS = {'Stitching': {'eff': 0.75}, '2nd Process': {'eff': 0.80}, 'Assembly': {'eff': 0.85}}
                        calculated_data = []
                        total_cost_usd = 0.0

                        for item in estimated_sam:
                            dept = item['Department']
                            sam = item['SAM']
                            eff = DEPT_SETTINGS.get(dept, {}).get('eff', 0.80)
                            
                            cost_idr = (sam / eff) * cpm_idr
                            cost_usd = cost_idr / fx_rate
                            total_cost_usd += cost_usd
                            
                            calculated_data.append({
                                'Process Name': item['Process'],
                                'Department': dept,
                                'SAM (Min)': sam,
                                'Target Eff (%)': f"{int(eff * 100)}%",
                                'CPM ($)': f"${cpm_usd:.4f}",
                                'Labor Cost ($)': round(cost_usd, 4),
                                'Equiv. Cost (IDR)': f"IDR {cost_idr:,.2f}"
                            })

                        df = pd.DataFrame(calculated_data)
                        
                        st.subheader("📊 Costing Breakdown Summary")
                        st.dataframe(df, use_container_width=True)
                        
                        st.success(f"**Total Labor Cost per Pair:** ${total_cost_usd:.4f} USD (Equivalent to IDR {total_cost_usd * fx_rate:,.2f})")
                        
                        # Export Excel File Button
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            df.to_excel(writer, sheet_name='Costing_Summary', index=False)
                        
                        st.download_button(
                            label="📥 Download Excel Report (.xlsx)",
                            data=buffer.getvalue(),
                            file_name="Footwear_Labor_Costing_Report.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    except Exception as e:
                        st.error(f"An error occurred: {e}")
