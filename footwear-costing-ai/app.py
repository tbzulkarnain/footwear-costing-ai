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

                        # 2. Inisialisasi Model Menggunakan gemini-3.6-flash (dengan Fallback)
                        target_model_name = 'gemini-3.6-flash'
                        try:
                            model = genai.GenerativeModel(target_model_name)
                        except Exception:
                            available_models = [
                                m.name for m in genai.list_models() 
                                if 'generateContent' in m.supported_generation_methods and 'flash' in m.name
                            ]
                            if available_models:
                                target_model_name = available_models[0]
                                model = genai.GenerativeModel(target_model_name)
                            else:
                                raise Exception("Tidak ditemukan model Flash yang mendukung generateContent.")

                        # 3. Prompt Visual Detection
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

                        # 4. Request ke Gemini AI
                        response = model.generate_content([img, prompt])
                        
                        raw_text = response.text
                        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                        
                        if json_match:
                            clean_text = json_match.group(0)
                        else:
                            clean_text = raw_text.strip()
                            
                        ai_data = json.loads(clean_text)

                        with st.expander("📄 View AI Visual Detection Results (Structured Data)", expanded=True):
                            st.json(ai_data)

                        # --- IE SAM BENCHMARK LOGIC (PYTHON COMPUTATION ENGINE) ---
                        IE_BENCHMARK = {
                            'cutting': {
                                'base': 2.0,
                                'panel_addon': 0.25
                            },
                            'stitching': {
                                'base': {'low-cut': 9.0, 'mid-cut': 11.0, 'high-cut': 13.0, 'boot': 15.0, 'slip-on': 7.5},
                                'complexity_add_on': {'simple': 0.0, 'medium': 2.5, 'complex': 5.5}
                            },
                            'assembly': {
                                'cementing': 8.5,
                                'vulcanized': 9.5,
                                'stitchdown': 11.0,
                                'injection': 6.0
                            },
                            'second_process': {'base': 2.0}
                        }

                        estimated_sam = []

                        # A. Process SAM Cutting
                        panel_cnt = int(ai_data.get('estimated_panel_count', 6))
                        cutting_sam = IE_BENCHMARK['cutting']['base'] + (max(0, panel_cnt - 4) * IE_BENCHMARK['cutting']['panel_addon'])
                        estimated_sam.append({
                            "Process": f"Upper Cutting ({panel_cnt} Panels)", 
                            "Department": "Cutting", 
                            "SAM": round(cutting_sam, 2)
                        })

                        # B. Process SAM Stitching
                        shoe_type = str(ai_data.get('shoe_type', 'low-cut')).lower()
                        base_stitch_sam = IE_BENCHMARK['stitching']['base'].get(shoe_type, 9.0)
                        estimated_sam.append({
                            "Process": f"Base Upper Stitching ({shoe_type.capitalize()})", 
                            "Department": "Stitching", 
                            "SAM": base_stitch_sam
                        })

                        complexity = str(ai_data.get('upper_complexity', 'medium')).lower()
                        cmplx_sam = IE_BENCHMARK['stitching']['complexity_add_on'].get(complexity, 2.5)
                        if cmplx_sam > 0:
                            estimated_sam.append({
                                "Process": f"Upper Complexity Add-on ({complexity.capitalize()})", 
                                "Department": "Stitching", 
                                "SAM": cmplx_sam
                            })

                        # C. Process SAM 2nd Process
                        has_2nd_proc = ai_data.get('second_process_detected', False)
                        if has_2nd_proc:
                            proc_detail = ai_data.get('second_process_details', 'Decorative Process')
                            estimated_sam.append({
                                "Process": f"2nd Process ({proc_detail})", 
                                "Department": "2nd Process", 
                                "SAM": IE_BENCHMARK['second_process']['base']
                            })

                        # D. Process SAM Assembly
                        bottom_const = str(ai_data.get('bottom_construction', 'cementing')).lower()
                        assembly_sam = IE_BENCHMARK['assembly'].get(bottom_const, 8.5)
                        estimated_sam.append({
                            "Process": f"Bottom Assembly & Lasting ({bottom_const.capitalize()})", 
                            "Department": "Assembly", 
                            "SAM": assembly_sam
                        })

                        # --- COST CALCULATION ---
                        DEPT_SETTINGS = {
                            'Cutting': {'eff': 0.85},
                            'Stitching': {'eff': 0.75}, 
                            '2nd Process': {'eff': 0.80}, 
                            'Assembly': {'eff': 0.85}
                        }
                        
                        calculated_data = []
                        total_cost_usd = 0.0
                        total_sam_min = 0.0

                        for item in estimated_sam:
                            dept = item['Department']
                            sam = item['SAM']
                            eff = DEPT_SETTINGS.get(dept, {}).get('eff', 0.80)

                            cost_idr = (sam / eff) * cpm_idr
                            cost_usd = cost_idr / fx_rate
                            
                            total_sam_min += sam
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

                        # Summary Metrics
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Total SAM (Minutes)", f"{total_sam_min:.2f} Min")
                        m2.metric("Total Labor Cost (USD)", f"${total_cost_usd:.4f}")
                        m3.metric("Total Labor Cost (IDR)", f"IDR {total_cost_usd * fx_rate:,.2f}")

                        # --- EXPORT TO EXCEL ---
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            df.to_excel(writer, sheet_name='Costing Summary', index=False)
                            
                            params_df = pd.DataFrame([
                                {"Parameter": "Monthly Salary (IDR)", "Value": monthly_salary},
                                {"Parameter": "FX Rate (USD/IDR)", "Value": fx_rate},
                                {"Parameter": "Monthly Effective Minutes", "Value": monthly_minutes},
                                {"Parameter": "CPM (IDR/min)", "Value": round(cpm_idr, 2)},
                                {"Parameter": "CPM (USD/min)", "Value": round(cpm_usd, 4)},
                                {"Parameter": "Detected Shoe Type", "Value": ai_data.get('shoe_type')},
                                {"Parameter": "Upper Complexity", "Value": ai_data.get('upper_complexity')},
                                {"Parameter": "Bottom Construction", "Value": ai_data.get('bottom_construction')}
                            ])
                            params_df.to_excel(writer, sheet_name='Parameters & Detection', index=False)

                        st.download_button(
                            label="📥 Download Excel Report (.xlsx)",
                            data=buffer.getvalue(),
                            file_name="Footwear_Labor_Costing_Report.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

                    except json.JSONDecodeError:
                        st.error("Gagal membaca respons AI sebagai JSON. Silakan coba klik tombol analisis sekali lagi.")
                    except Exception as e:
                        st.error(f"Terjadi kesalahan saat memproses data: {e}")
