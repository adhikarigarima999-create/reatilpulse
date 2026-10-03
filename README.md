# 📊 RetailPulse Analytics Platform

![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)
![Render](https://img.shields.io/badge/Render-%46E3B7?style=for-the-badge&logo=render&logoColor=white)

RetailPulse is a full-stack, cloud-hosted analytics platform designed to ingest raw e-commerce CSV data, process it through a robust SQL pipeline, and serve actionable insights, A/B testing simulations, and machine learning predictions through a dynamic React frontend.

**🔴 Live Demo:** [https://retailpulse-fastapi.onrender.com](https://retailpulse-fastapi.onrender.com)

---

## 🚀 Features & Architecture

### 1. 🔄 Automated Data Pipeline (ELT)
- **Upload & Ingestion:** Users can upload custom CSV datasets (`orders`, `customers`, `order_items`, `payments`, `reviews`) directly through the React UI.
- **Supabase Integration:** The FastAPI backend streams the uploaded data directly into a managed Supabase PostgreSQL database.
- **SQL Transformations:** Upon upload, the backend automatically triggers a series of SQL views (`staging` -> `intermediate` -> `marts`) to clean, join, and aggregate the raw data into business-ready fact tables (`fct_orders`, `fct_customers`).

### 2. 📈 Exploratory Data Analysis (EDA) Dashboard
- A dynamic, interactive React dashboard built with Recharts and Tailwind CSS.
- Visualizes key business metrics such as Total Revenue, Repeat Purchase Rates, and Late Delivery Rates.
- Uses **In-Memory Caching** on the FastAPI layer to ensure sub-millisecond response times, bypassing network bottlenecks.

### 3. 🧪 A/B Testing Simulator
- Simulates the impact of promotional campaigns (e.g., offering a discount to drive repeat purchases).
- Powered by `statsmodels` (Proportions Z-Test) on the backend to calculate statistical significance, p-values, absolute lift, and incremental revenue.
- Optimized with **Numpy Vectorization**, allowing the simulation to instantly process and calculate probabilities for over 100,000 customers in less than `0.001` seconds.

### 4. 🤖 Machine Learning Predictor
- Uses `scikit-learn` Logistic Regression to predict the probability of a specific customer making a repeat purchase based on their initial order characteristics (e.g., order value, payment type, delivery performance).
- The model is dynamically trained on the latest available data in the Supabase database.

---

## 🛠️ Tech Stack

- **Frontend:** React, Vite, Tailwind CSS, Recharts, Lucide Icons
- **Backend:** Python, FastAPI, Uvicorn, Pandas, Numpy, Scikit-Learn, Statsmodels, SQLAlchemy
- **Database:** PostgreSQL (Hosted on Supabase)
- **Deployment:** Render (Web Service blueprint via `render.yaml`)

---

## 🚦 How to Test the Platform

1. **Visit the Live Site:** Navigate to the deployed Render URL.
2. **Download Sample Data:** Go to the **Upload Data** tab and click **"Download Sample CSVs"**. This will download a zip file containing a lightweight, 500-row sample of the required tables.
3. **Upload & Process:** Extract the zip file, drag the 5 CSVs into the upload dropzone, and click Process. 
4. **Verify:** You will immediately see the "Overview" metrics drop to reflect the smaller sample size, proving the end-to-end cloud pipeline is successfully ingesting, transforming, and serving your new data!

---

## ⚙️ Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+

### Backend Setup
```bash
# Install Python dependencies
pip install -r requirements.txt

# Start the FastAPI server (runs on localhost:8000)
uvicorn backend.main:app --reload
```

### Frontend Setup
```bash
cd frontend

# Install Node dependencies
npm install

# Start the Vite development server
npm run dev
```
