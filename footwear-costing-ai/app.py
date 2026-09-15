import streamlit as st
from PIL import Image
import pandas as pd
import io
import requests
import base64

# --- CONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Footwear Labor Costing AI",
    page_icon="👟",
    layout="wide"
)

st.title("👟 Footwear Labor Costing (FOB) AI Engine")
st.markdown("""
Aplikasi ini memanfaatkan **Gemini Vision AI** untuk menganalisis foto fisik sepatu, 
mengekstraksi fitur konstruksi, memetakan estimasi **SAM (Standard Allowed Minutes)** IE, 
dan menghitung **Labor Cost (FOB)** secara otomatis.
""")

st.sidebar.header("⚙️ Pengaturan Parameter Costing")

# --- AMBIL API KEY DARI SECRETS ATAU INPUT SIDEBAR ---
secret_api_key = st.secrets.get("GEMINI_API_KEY", "")

api_key = st.sidebar.text_input(
    "Gemini API Key", 
    value=secret_api_key, 
    type="password", 
    help="Masukkan API Key Gemini (AQ... atau AIzaSy...) kamu"
)

gaji_bulan = st.sidebar.number_input("Gaji Operator / Bulan (Rp)", value=5000000, step=250000)
fx_rate = st.sidebar.number_input("Kurs USD (1 USD = Rp...)", value=16800, step=100)
menit_bulan = st.sidebar.number_input("Menit Kerja Efektif / Bulan", value=10400, help="Standar 173.33 jam/bulan")

# Hitung CPM
cpm_rp = gaji_bulan / menit_bulan
cpm_usd = cpm_rp / fx_rate

st.sidebar.metric("CPM (Rp/menit)", f"Rp {cpm_rp:.2f}")
st.sidebar.metric("CPM (USD/menit)", f"${cpm_usd:.4f}")

# Layout Dua Kolom
col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("1. Upload Foto Sepatu")
    uploaded_file = st.file_uploader("Pilih gambar sepatu (JPG/PNG)", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        img = Image.open(uploaded_file)
        st.image(img, caption="Preview Sepatu", use_container_width=True)

with col2:
    st.subheader("2. Analisis & Estimasi Costing")
    
    if uploaded_file is not None:
        if st.button("🚀 Analisis Sepatu & Hitung Costing", type="primary"):
            if not api_key:
                st.error("Silakan masukkan Gemini API Key di sidebar atau konfigurasi Secrets Streamlit!")
            else:
                with st.spinner("Sedang menganalisis gambar memakai Gemini AI..."):
                    try:
                        # 1. Prepare Image to Base64
                        img_byte_arr = io.BytesIO()
                        img_format = img.format if img.format else 'JPEG'
                        img.save(img_byte_arr, format=img_format)
                        img_bytes = img_byte_arr.getvalue()
                        base64_image = base64.b64encode(img_bytes).decode('utf-8')
                        
                        prompt = """
                        Kamu adalah seorang Industrial Engineering & Costing Specialist di industri footwear.
                        Analisis foto fisik sepatu ini dan berikan output dalam format terstruktur dengan poin-poin berikut:

                        1. Shoe Type (Low-cut / Mid-cut / High-cut / Boot / Slip-on)
                        2. Upper Complexity (Simple / Medium / Complex) - berdasarkan jumlah panel cutting dan layer jahitan
                        3. Material Upper (Estimated: Mesh, Synthetic Leather, Genuine Leather, Knit, Canvas, dll.)
                        4. 2nd Process Detected (Ada/Tidak ada: Embroidery, Screen Printing, Heat Transfer, Emboss, TPU welding, dll.)
                        5. Bottom Construction (Cementing, Vulcanized, Stitchdown, Injection, dll.)
                        6. Estimated Feature Breakdown untuk acuan SAM IE:
                           - Upper Cutting Panel Count: (Estimasi jumlah potongan bahan)
                           - Stitching Lines Complexity: (Low/Medium/High)
                           - Secondary Process Count: (Jumlah proses dekoratif/luar)

                        Jawab langsung dengan poin-poin data tanpa kata pembuka formal.
                        """
                        
                        # 2. Endpoint REST Gemini API
                        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
                        
                        # Format Header Khusus untuk Kunci AQ...
                        clean_key = api_key.strip()
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
                        
                        with st.expander("📄 Lihat Hasil Deteksi Visual AI", expanded=True):
                            st.write(output_text)
                        
                        # --- LOGIKA SAM IE ---
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

                        if 'ada' in ai_text or 'yes' in ai_text:
                            estimated_sam.append({"Process": "Secondary Process (Punching/Logo)", "Department": "2nd Process", "SAM": IE_BENCHMARK['second_process']['base']})

                        if 'cementing' in ai_text:
                            estimated_sam.append({"Process": "Bottom Assembly & Lasting (Cementing)", "Department": "Assembly", "SAM": IE_BENCHMARK['assembly']['cementing']})
                        else:
                            estimated_sam.append({"Process": "Bottom Assembly & Lasting (Standard)", "Department": "Assembly", "SAM": 8.0})

                        # --- KALKULASI COST ---
                        DEPT_SETTINGS = {'Stitching': {'eff': 0.75}, '2nd Process': {'eff': 0.80}, 'Assembly': {'eff': 0.85}}
                        calculated_data = []
                        total_cost_usd = 0.0

                        for item in estimated_sam:
                            dept = item['Department']
                            sam = item['SAM']
                            eff = DEPT_SETTINGS.get(dept, {}).get('eff', 0.80)
                            
                            cost_rp = (sam / eff) * cpm_rp
                            cost_usd = cost_rp / fx_rate
                            total_cost_usd += cost_usd
                            
                            calculated_data.append({
                                'Process Name': item['Process'],
                                'Department': dept,
                                'SAM (Min)': sam,
                                'Target Eff (%)': f"{int(eff * 100)}%",
                                'CPM ($)': f"${cpm_usd:.4f}",
                                'Labor Cost ($)': round(cost_usd, 4),
                                'Equiv. Cost (Rp)': f"Rp {cost_rp:,.2f}"
                            })

                        df = pd.DataFrame(calculated_data)
                        
                        st.subheader("📊 Rekap Kalkulasi Costing")
                        st.dataframe(df, use_container_width=True)
                        
                        st.success(f"**Total Labor Cost per Pasang:** ${total_cost_usd:.4f} USD (Setara Rp {total_cost_usd * fx_rate:,.2f})")
                        
                        # Export Excel File Button
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            df.to_excel(writer, sheet_name='Costing_Summary', index=False)
                        
                        st.download_button(
                            label="📥 Download Laporan Excel (.xlsx)",
                            data=buffer.getvalue(),
                            file_name="Hasil_Kalkulasi_Labor_Cost.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    except Exception as e:
                        st.error(f"Terjadi kesalahan: {e}")
