# 👟 Footwear Labor Costing (FOB) AI Engine

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://footwear-costing-ai-2ncfyn6gmecat7u5m4kzyf.streamlit.app/)

An AI-driven Industrial Engineering application powered by **Google Gemini Vision API** to analyze footwear photos, extract construction details, map estimated **SAM (Standard Allowed Minutes)**, and compute **Labor Cost (FOB)** automatically.

🚀 **Live Interactive Demo:** [Launch App Here](https://footwear-costing-ai-2ncfyn6gmecat7u5m4kzyf.streamlit.app/)

---

## 📌 Problem & Solution

In footwear manufacturing, calculating standard labor costs and Standard Allowed Minutes (SAM) manually from physical shoe samples takes time and requires deep IE domain knowledge. 

This tool automates the initial estimation by combining **Computer Vision (AI)** with **Industrial Engineering benchmark rules**:
1. Upload a photo of the shoe.
2. AI extracts key construction parameters (upper complexity, bottom construction, 2nd process).
3. The engine automatically maps estimated SAM per department and calculates total labor cost per pair in both USD & IDR.

---

## ✨ Key Features

- **Automated Feature Extraction:** Identifies shoe type, upper materials, complexity levels, secondary decorative processes, and bottom construction.
- **Dynamic SAM Mapping:** Maps IE benchmarks for Stitching, Assembly, and 2nd Process operations based on visual parameters.
- **Custom Cost Parameters:** Configurable operator monthly salary, effective working minutes, target efficiencies, and exchange rates.
- **Costing Breakdown Table:** Detailed output per process including Target Efficiency, CPM (Cost Per Minute), and Labor Cost per pair.
- **Excel Report Export:** Downloadable `.xlsx` costing summary report for factory quotation and records.

---

## 🛠️ Tech Stack

- **Frontend & App Framework:** [Streamlit](https://streamlit.io/)
- **AI & Computer Vision Model:** [Google Gemini 3.6 Flash API](https://ai.google.dev/)
- **Data Manipulation:** Pandas
- **File Export:** OpenPyXL
- **Language:** Python 3.10+
