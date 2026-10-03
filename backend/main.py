from fastapi import FastAPI, HTTPException, UploadFile, File
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
import urllib.parse
from sqlalchemy import create_engine, text
from pathlib import Path
import io
from statsmodels.stats.proportion import proportions_ztest
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import os

app = FastAPI(title="RetailPulse API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Database Connection (Supabase PostgreSQL) ---
DATABASE_URL = os.environ.get("DATABASE_URL", None)
if not DATABASE_URL:
    password = urllib.parse.quote("Teekhi Mrichi")
    DATABASE_URL = f"postgresql+psycopg2://postgres.bvblceezljunzicpkthd:{password}@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"

engine = create_engine(DATABASE_URL)
ROOT = Path(__file__).resolve().parents[1]

# --- Required columns for schema validation ---
REQUIRED_COLUMNS = {
    "orders": ["order_id", "customer_id", "order_status"],
    "customers": ["customer_id", "city", "state"],
    "order_items": ["order_id", "item_no", "price"],
    "payments": ["order_id", "payment_type", "payment_value"],
    "reviews": ["order_id", "review_score"],
}

FILE_TABLE_MAP = {
    "orders": "orders",
    "customers": "customers",
    "order_items": "order_items",
    "payments": "payments",
    "reviews": "reviews",
}


def rebuild_views(schema: str = "public"):
    """Re-run Postgres SQL transforms to rebuild all views."""
    sql_files = [
        ROOT / "sql" / "pg_01_staging.sql",
        ROOT / "sql" / "pg_02_intermediate.sql",
        ROOT / "sql" / "pg_03_marts.sql",
    ]
    with engine.connect() as conn:
        conn.execute(text(f"SET search_path TO {schema}, public"))
        for f in sql_files:
            if f.exists():
                sql_lines = [line for line in f.read_text().splitlines() if not line.strip().startswith("--")]
                clean_sql = "\n".join(sql_lines)
                for stmt in clean_sql.split(";"):
                    stmt = stmt.strip()
                    if stmt:
                        conn.execute(text(stmt))
                conn.commit()


@app.post("/api/upload")
async def upload_csvs(session_id: str, files: List[UploadFile] = File(...)):
    """Upload custom CSV files, validate, write to Supabase, and rebuild views."""
    global _model_cache, _data_cache
    if _model_cache and session_id in _model_cache:
        del _model_cache[session_id]
    if _data_cache and session_id in _data_cache:
        del _data_cache[session_id]

    matched = {}
    errors = []

    for f in files:
        name_lower = f.filename.lower()
        matched_table = None
        for key in FILE_TABLE_MAP:
            if key in name_lower:
                matched_table = FILE_TABLE_MAP[key]
                break
        if not matched_table:
            errors.append(f"Could not match '{f.filename}' to any table. Expected filenames containing: {list(FILE_TABLE_MAP.keys())}")
            continue

        content = await f.read()
        df = pd.read_csv(io.BytesIO(content))

        # Validate required columns
        required = REQUIRED_COLUMNS.get(matched_table, [])
        missing = [c for c in required if c not in df.columns]
        if missing:
            errors.append(f"'{f.filename}' is missing required columns: {missing}")
            continue

        matched[matched_table] = df

    if errors:
        return {"success": False, "errors": errors, "tables_loaded": list(matched.keys())}

    if len(matched) < 5:
        missing_tables = [t for t in FILE_TABLE_MAP.values() if t not in matched]
        return {"success": False, "errors": [f"Missing files for tables: {missing_tables}"], "tables_loaded": list(matched.keys())}

    # Create session schema
    safe_schema = f"session_{session_id}"
    with engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {safe_schema}"))
        conn.execute(text(f"SET search_path TO {safe_schema}"))
        for table_name in matched.keys():
            conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
        conn.commit()

    # Write all tables to the session schema
    for table_name, df in matched.items():
        df.to_sql(table_name, engine, schema=safe_schema, if_exists='replace', index=False)

    # Rebuild views inside the session schema
    rebuild_views(safe_schema)

    return {
        "success": True,
        "errors": [],
        "tables_loaded": list(matched.keys()),
        "message": f"Successfully uploaded {sum(len(df) for df in matched.values())} total rows across {len(matched)} tables."
    }


_data_cache = {}

def load_data(session_id: str = "public"):
    global _data_cache
    if session_id in _data_cache:
        return _data_cache[session_id]

    try:
        schema = f"session_{session_id}" if session_id != "public" else "public"
        with engine.connect() as conn:
            # Check if schema exists, if not fallback to public
            res = conn.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = :s"), {"s": schema}).fetchone()
            if not res:
                schema = "public"
            conn.execute(text(f"SET search_path TO {schema}, public"))
            fct_orders = pd.read_sql("SELECT * FROM fct_orders", conn)
            fct_customers = pd.read_sql("SELECT * FROM fct_customers", conn)
        
        _data_cache[session_id] = (fct_orders, fct_customers)
        return _data_cache[session_id]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/eda")
def get_eda(session_id: str = "public"):
    fct_orders, fct_customers = load_data(session_id)

    total_revenue = float(fct_orders['order_value'].sum())
    repeat_rate = float(fct_customers['is_repeat_customer'].mean() * 100)
    late_rate = float(fct_orders['was_late'].mean() * 100)

    # Order Value Distribution (histogram data)
    counts, bins = np.histogram(fct_orders['order_value'].dropna(), bins=40)
    order_dist = [{"bin": f"{bins[i]:.0f}-{bins[i+1]:.0f}", "count": int(c)} for i, c in enumerate(counts)]

    # Repeat rate by state
    state_summary = fct_customers.groupby("state")["is_repeat_customer"].mean().mul(100).reset_index().sort_values("is_repeat_customer", ascending=False)
    state_rate = state_summary.to_dict(orient="records")

    # Review score: Late vs On-Time
    df_l = fct_orders.dropna(subset=["review_score"]).copy()
    df_l["delivery"] = df_l["was_late"].map({1: "Late", 0: "On time"})
    score_summary = df_l.groupby("delivery")["review_score"].mean().reset_index()
    review_by_delivery = score_summary.to_dict(orient="records")

    return {
        "metrics": {
            "total_revenue": total_revenue,
            "repeat_rate": repeat_rate,
            "late_rate": late_rate,
        },
        "order_distribution": order_dist,
        "repeat_rate_by_state": state_rate,
        "review_by_delivery": review_by_delivery
    }


class ABTestRequest(BaseModel):
    lift_pp: float


@app.post("/api/ab_test")
def run_ab_test(req: ABTestRequest, session_id: str = "public"):
    _, fct_customers = load_data(session_id)
    lift_input = req.lift_pp / 100.0

    np.random.seed(7)
    df_ab = fct_customers.copy()
    df_ab["group"] = np.random.choice(["control", "treatment"], size=len(df_ab), p=[0.5, 0.5])

    base_prob = float(df_ab["is_repeat_customer"].mean())

    p_array = np.where(df_ab["group"] == "treatment", base_prob + lift_input, base_prob)
    p_array = np.clip(p_array, 0, 1)
    df_ab["repeat_purchase_outcome"] = np.random.binomial(1, p_array)

    counts = df_ab.groupby("group")["repeat_purchase_outcome"].agg(["sum", "count"])
    successes = [counts.loc["treatment", "sum"], counts.loc["control", "sum"]]
    nobs = [counts.loc["treatment", "count"], counts.loc["control", "count"]]
    z_stat, p_val = proportions_ztest(successes, nobs, alternative="larger")
    rate_t = float(successes[0] / nobs[0])
    rate_c = float(successes[1] / nobs[1])

    lift_actual = (rate_t - rate_c) * 100
    avg_ltv = float(df_ab["lifetime_value"].mean())
    incremental_customers = lift_actual / 100 * len(df_ab[df_ab.group == "treatment"])
    incremental_revenue = float(incremental_customers * avg_ltv)
    discount_cost = float(0.10 * df_ab.loc[df_ab.group == "treatment", "avg_order_value"].sum())

    return {
        "treatment_rate": rate_t,
        "control_rate": rate_c,
        "absolute_lift_pp": lift_actual,
        "z_stat": float(z_stat),
        "p_val": float(p_val),
        "incremental_revenue": incremental_revenue,
        "discount_cost": discount_cost,
        "recommend_ship": bool(p_val < 0.05 and incremental_revenue > discount_cost)
    }


_model_cache = {}


def get_model(session_id: str = "public"):
    global _model_cache
    if session_id in _model_cache:
        return _model_cache[session_id]

    schema = f"session_{session_id}" if session_id != "public" else "public"
    with engine.connect() as conn:
        res = conn.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = :s"), {"s": schema}).fetchone()
        if not res:
            schema = "public"
        conn.execute(text(f"SET search_path TO {schema}, public"))
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

    _model_cache[session_id] = (model, scaler, X.columns)
    return _model_cache[session_id]


class PredictRequest(BaseModel):
    order_value: float
    installments: int
    review_score: int
    was_late: int
    payment_type: str


@app.post("/api/predict")
def predict_repeat(req: PredictRequest, session_id: str = "public"):
    model, scaler, feature_cols = get_model(session_id)

    input_data = {
        "order_value": [req.order_value],
        "was_late": [req.was_late],
        "installments": [req.installments],
        "review_score": [req.review_score],
        "payment_type_credit_card": [1 if req.payment_type == "credit_card" else 0],
        "payment_type_debit_card": [1 if req.payment_type == "debit_card" else 0],
        "payment_type_voucher": [1 if req.payment_type == "voucher" else 0],
        "payment_type_unknown": [1 if req.payment_type == "unknown" else 0]
    }

    for c in feature_cols:
        if c not in input_data:
            input_data[c] = [0]

    sim_df = pd.DataFrame(input_data)[feature_cols]
    sim_s = scaler.transform(sim_df)
    prob = model.predict_proba(sim_s)[0, 1]

    return {"probability_repeat": float(prob)}

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

# Mount the 'charts' folder for any dynamically generated images
app.mount('/charts', StaticFiles(directory=str(ROOT / 'charts')), name='charts')

# Mount the built React frontend
dist_path = ROOT / 'frontend' / 'dist'
if dist_path.exists():
    app.mount('/', StaticFiles(directory=str(dist_path), html=True), name='frontend')
else:
    @app.get('/')
    def fallback_index():
        return {"message": "Frontend not built yet. Please run 'npm run build' inside the 'frontend' directory."}

