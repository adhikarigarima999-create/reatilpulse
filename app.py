import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import plotly.express as px
from pathlib import Path
from statsmodels.stats.proportion import proportions_ztest
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, confusion_matrix

st.set_page_config(page_title="RetailPulse", layout="wide")

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "retailpulse_raw.db"

# Helper for SQL transforms
def run_sql_transforms():
    conn = sqlite3.connect(DB_PATH)
    sql_files = [
        ROOT / "sql" / "01_staging.sql",
        ROOT / "sql" / "02_intermediate.sql",
        ROOT / "sql" / "03_marts.sql",
    ]
    for f in sql_files:
        if f.exists():
            conn.executescript(f.read_text())
    conn.commit()
    conn.close()

# Sidebar
st.sidebar.title("RetailPulse")
mode = st.sidebar.radio("Mode", ["Demo Mode (Kaggle Data)", "Upload Custom Data"])

def check_schema(df, required_columns, name):
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        st.sidebar.warning(f"{name} is missing columns: {', '.join(missing)}")
        return False
    return True

if mode == "Upload Custom Data":
    st.sidebar.subheader("Upload CSV Files")
    uploaded_files = st.sidebar.file_uploader("Upload all dataset CSVs (orders, customers, items, payments, reviews)", type=["csv"], accept_multiple_files=True)

    if st.sidebar.button("Process Uploaded Data"):
        if uploaded_files:
            with st.spinner("Processing custom data..."):
                try:
                    df_orders = df_cust = df_items = df_pay = df_rev = None
                    for f in uploaded_files:
                        if "orders_dataset" in f.name: df_orders = pd.read_csv(f)
                        elif "customers_dataset" in f.name: df_cust = pd.read_csv(f)
                        elif "order_items_dataset" in f.name: df_items = pd.read_csv(f)
                        elif "order_payments_dataset" in f.name: df_pay = pd.read_csv(f)
                        elif "order_reviews_dataset" in f.name: df_rev = pd.read_csv(f)
                    
                    if not all(df is not None for df in [df_orders, df_cust, df_items, df_pay, df_rev]):
                        st.sidebar.error("Could not find all 5 required files based on names. Please ensure filenames include 'orders_dataset', 'customers_dataset', 'order_items_dataset', 'order_payments_dataset', and 'order_reviews_dataset'.")
                    else:

                        # Validate basic columns
                        v1 = check_schema(df_orders, ['order_id', 'customer_id', 'order_status', 'order_purchase_timestamp'], "Orders")
                        v2 = check_schema(df_cust, ['customer_id', 'customer_unique_id', 'customer_state'], "Customers")
                        
                        if v1 and v2:
                            conn = sqlite3.connect(DB_PATH)
                            # Process same as Kaggle Data logic
                            cust_map = df_cust[['customer_id', 'customer_unique_id']].drop_duplicates()
                            
                            customers_table = (
                                df_cust[['customer_unique_id', 'customer_city', 'customer_state']]
                                .drop_duplicates(subset=['customer_unique_id'])
                                .rename(columns={
                                    'customer_unique_id': 'customer_id',
                                    'customer_city': 'city',
                                    'customer_state': 'state'
                                })
                            )
    
                            df_orders = df_orders.merge(cust_map, on='customer_id', how='inner')
                            orders_table = pd.DataFrame({
                                'order_id': df_orders['order_id'],
                                'customer_id': df_orders['customer_unique_id'],
                                'order_status': df_orders['order_status'],
                                'purchase_ts': df_orders['order_purchase_timestamp'],
                                'approved_ts': df_orders.get('order_approved_at'),
                                'estimated_delivery_ts': df_orders.get('order_estimated_delivery_date'),
                                'delivered_ts': df_orders.get('order_delivered_customer_date')
                            })
                            
                            order_items_table = pd.DataFrame({
                                'order_id': df_items['order_id'],
                                'item_no': df_items['order_item_id'],
                                'product_id': df_items['product_id'],
                                'seller_id': df_items['seller_id'],
                                'category': df_items.get('product_category_name', 'other'),
                                'price': df_items['price'],
                                'freight_value': df_items['freight_value']
                            })
                            
                            payments_table = pd.DataFrame({
                                'order_id': df_pay['order_id'],
                                'payment_type': df_pay['payment_type'],
                                'installments': df_pay['payment_installments'],
                                'payment_value': df_pay['payment_value']
                            })
    
                            reviews_table = pd.DataFrame({
                                'order_id': df_rev['order_id'],
                                'review_score': df_rev['review_score']
                            })
    
                            customers_table.to_sql("customers", conn, if_exists="replace", index=False)
                            orders_table.to_sql("orders", conn, if_exists="replace", index=False)
                            order_items_table.to_sql("order_items", conn, if_exists="replace", index=False)
                            payments_table.to_sql("payments", conn, if_exists="replace", index=False)
                            reviews_table.to_sql("reviews", conn, if_exists="replace", index=False)
                            conn.close()
    
                            run_sql_transforms()
                        st.sidebar.success("Custom data processed & marts built!")
                        st.cache_data.clear()
                except Exception as e:
                    st.sidebar.error(f"Error: {e}")
        else:
            st.sidebar.warning("Please upload all 5 CSV files.")

# --- Data Loading ---
@st.cache_data
def load_data():
    if not DB_PATH.exists():
        return pd.DataFrame(), pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    try:
        fct_orders = pd.read_sql("SELECT * FROM fct_orders", conn)
        fct_customers = pd.read_sql("SELECT * FROM fct_customers", conn)
        conn.close()
        return fct_orders, fct_customers
    except Exception as e:
        conn.close()
        return pd.DataFrame(), pd.DataFrame()

fct_orders, fct_customers = load_data()

if fct_orders.empty or fct_customers.empty:
    st.warning("No data found or database missing tables. Please run Demo Mode pipeline or Upload Custom Data.")
    st.stop()

# --- Main Page ---
st.divider()

if True:
    st.header("Overview & EDA")
    col1, col2, col3 = st.columns(3)
    
    total_revenue = fct_orders['order_value'].sum()
    repeat_rate = fct_customers['is_repeat_customer'].mean() * 100
    late_rate = fct_orders['was_late'].mean() * 100
    
    col1.metric("Total Revenue", f"R$ {total_revenue:,.0f}")
    col2.metric("Repeat Rate", f"{repeat_rate:.1f}%")
    col3.metric("Late Delivery Rate", f"{late_rate:.1f}%")
    
    st.subheader("Order Value Distribution")
    fig1 = px.histogram(fct_orders, x="order_value", nbins=40, title="Order Value Distribution", color_discrete_sequence=["steelblue"])
    st.plotly_chart(fig1, use_container_width=True)
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Repeat Rate by State")
        state_summary = fct_customers.groupby("state")["is_repeat_customer"].mean().mul(100).reset_index().sort_values("is_repeat_customer", ascending=False)
        fig2 = px.bar(state_summary, x="state", y="is_repeat_customer", title="Repeat-Customer Rate by State", color="is_repeat_customer")
        st.plotly_chart(fig2, use_container_width=True)
        
    with col_b:
        st.subheader("Review Score: Late vs. On-Time")
        df_l = fct_orders.dropna(subset=["review_score"]).copy()
        df_l["delivery"] = df_l["was_late"].map({1: "Late", 0: "On time"})
        score_summary = df_l.groupby("delivery")["review_score"].mean().reset_index()
        fig3 = px.bar(score_summary, x="delivery", y="review_score", title="Average Review Score", color="delivery")
        fig3.update_yaxes(range=[0, 5])
        st.plotly_chart(fig3, use_container_width=True)

st.divider()
if True:
    st.header("A/B Testing Simulator: 10% Discount Promo")
    st.markdown("Simulate offering a 10% discount on the 2nd purchase to a random half of customers.")
    
    lift_input = st.slider("Simulated Promo Lift (Percentage Points)", 0.0, 10.0, 4.0, 0.5) / 100.0
    
    if st.button("Run Simulation"):
        np.random.seed(7)
        df_ab = fct_customers.copy()
        df_ab["group"] = np.random.choice(["control", "treatment"], size=len(df_ab), p=[0.5, 0.5])
        
        base_prob = df_ab["is_repeat_customer"].mean()
        
        def outcome(row):
            p = base_prob + (lift_input if row["group"] == "treatment" else 0.0)
            p = min(max(p, 0), 1)
            return np.random.binomial(1, p)
            
        df_ab["repeat_purchase_outcome"] = df_ab.apply(outcome, axis=1)
        
        counts = df_ab.groupby("group")["repeat_purchase_outcome"].agg(["sum", "count"])
        successes = [counts.loc["treatment", "sum"], counts.loc["control", "sum"]]
        nobs = [counts.loc["treatment", "count"], counts.loc["control", "count"]]
        z_stat, p_val = proportions_ztest(successes, nobs, alternative="larger")
        rate_t = successes[0] / nobs[0]
        rate_c = successes[1] / nobs[1]
        
        st.write(f"**Treatment Repeat Rate:** {rate_t:.4f}")
        st.write(f"**Control Repeat Rate:** {rate_c:.4f}")
        lift_pp = (rate_t - rate_c) * 100
        st.write(f"**Absolute Lift:** {lift_pp:.2f} pp")
        st.write(f"**z-statistic:** {z_stat:.3f} | **p-value:** {p_val:.4f}")
        
        avg_ltv = df_ab["lifetime_value"].mean()
        incremental_customers = lift_pp / 100 * len(df_ab[df_ab.group == "treatment"])
        incremental_revenue = incremental_customers * avg_ltv
        discount_cost = 0.10 * df_ab.loc[df_ab.group == "treatment", "avg_order_value"].sum()
        
        col1, col2 = st.columns(2)
        col1.metric("Modeled Incremental Revenue", f"R$ {incremental_revenue:,.0f}")
        col2.metric("Modeled Discount Cost", f"R$ {discount_cost:,.0f}")
        
        if p_val < 0.05 and incremental_revenue > discount_cost:
            st.success("RECOMMENDATION: SHIP. Lift is significant and ROI is positive.")
        else:
            st.error("RECOMMENDATION: DO NOT SHIP AS-IS. Cost exceeds benefit or non-significant.")

st.divider()
if True:
    st.header("Repeat Purchase Predictor")
    
    @st.cache_data
    def train_model():
        conn = sqlite3.connect(DB_PATH)
        q = """
        SELECT
            fo.order_id,
            fo.order_value,
            fo.was_late,
            fo.review_score,
            fo.payment_type,
            fo.installments,
            fc.is_repeat_customer
        FROM fct_orders fo
        JOIN fct_customers fc ON fc.customer_id = fo.customer_id
        WHERE fo.order_seq_num = 1
        """
        df = pd.read_sql(q, conn)
        conn.close()
        
        df["review_score"] = df["review_score"].fillna(df["review_score"].median())
        df["order_value"] = df["order_value"].fillna(df["order_value"].median())
        df["installments"] = df["installments"].fillna(1)
        df["was_late"] = df["was_late"].fillna(0)
        df["payment_type"] = df["payment_type"].fillna("unknown")
        df["is_repeat_customer"] = df["is_repeat_customer"].fillna(0)

        features_num = ["order_value", "was_late", "installments", "review_score"]
        features_cat = ["payment_type"]
        
        X = pd.get_dummies(df[features_num + features_cat], columns=features_cat, drop_first=True)
        y = df["is_repeat_customer"]
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)
        
        model = LogisticRegression(max_iter=1000, class_weight="balanced")
        model.fit(X_train_s, y_train)
        
        y_proba = model.predict_proba(X_test_s)[:, 1]
        y_pred = model.predict(X_test_s)
        auc = roc_auc_score(y_test, y_proba)
        cm = confusion_matrix(y_test, y_pred)
        
        coefs = pd.Series(model.coef_[0], index=X.columns).sort_values(key=abs, ascending=False)
        return model, scaler, auc, cm, coefs, X.columns

    with st.spinner("Training model..."):
        try:
            model, scaler, auc, cm, coefs, feature_cols = train_model()
            
            st.subheader(f"Model Performance (ROC-AUC: {auc:.3f})")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Confusion Matrix**")
                fig_cm = px.imshow(cm, text_auto=True, labels=dict(x="Predicted", y="Actual"), x=["One-time", "Repeat"], y=["One-time", "Repeat"])
                st.plotly_chart(fig_cm, use_container_width=True)
            with col2:
                st.write("**Feature Importances (Absolute)**")
                fig_coef = px.bar(x=coefs.values, y=coefs.index, orientation='h', title="Standardized Coefficients")
                st.plotly_chart(fig_coef, use_container_width=True)
                
            st.subheader("Predict Customer Outcome")
            st.write("Simulate a first order to predict if the customer will return.")
            
            c1, c2, c3, c4 = st.columns(4)
            sim_val = c1.number_input("Order Value", min_value=0.0, value=100.0)
            sim_installments = c2.number_input("Installments", min_value=1, value=1)
            sim_review = c3.slider("Review Score", 1, 5, 5)
            sim_late = c4.selectbox("Was Late?", [0, 1])
            sim_payment = st.selectbox("Payment Type", ["credit_card", "boleto", "voucher", "debit_card", "unknown"])
            
            if st.button("Predict"):
                input_data = {
                    "order_value": [sim_val],
                    "was_late": [sim_late],
                    "installments": [sim_installments],
                    "review_score": [sim_review],
                    "payment_type_credit_card": [1 if sim_payment=="credit_card" else 0],
                    "payment_type_debit_card": [1 if sim_payment=="debit_card" else 0],
                    "payment_type_voucher": [1 if sim_payment=="voucher" else 0],
                    "payment_type_unknown": [1 if sim_payment=="unknown" else 0]
                }
                for c in feature_cols:
                    if c not in input_data:
                        input_data[c] = [0]
                
                sim_df = pd.DataFrame(input_data)[feature_cols]
                sim_s = scaler.transform(sim_df)
                prob = model.predict_proba(sim_s)[0, 1]
                
                st.success(f"Probability of Repeat Purchase: {prob*100:.1f}%")
        except Exception as e:
            st.error(f"Could not train model. Are there enough records? Error: {e}")
