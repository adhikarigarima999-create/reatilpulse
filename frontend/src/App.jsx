import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer 
} from 'recharts';
import { 
  LineChart, Activity, ShoppingCart, Users, Play, Target, Upload, CheckCircle, AlertCircle
} from 'lucide-react';

const API_BASE = "/api";

function App() {
  const [activeTab, setActiveTab] = useState("overview");
  
  // EDA State
  const [edaData, setEdaData] = useState(null);
  const [loadingEda, setLoadingEda] = useState(false);

  // A/B Test State
  const [liftInput, setLiftInput] = useState(4.0);
  const [abResult, setAbResult] = useState(null);
  const [loadingAb, setLoadingAb] = useState(false);

  // Predict State
  const [predForm, setPredForm] = useState({
    order_value: 100, installments: 1, review_score: 5, was_late: 0, payment_type: 'credit_card'
  });
  const [predResult, setPredResult] = useState(null);
  const [loadingPred, setLoadingPred] = useState(false);

  // Upload State
  const [uploadFiles, setUploadFiles] = useState(null);
  const [uploadResult, setUploadResult] = useState(null);
  const [loadingUpload, setLoadingUpload] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  // Session Management (Multi-Tenancy)
  const getSessionId = () => {
    let sid = sessionStorage.getItem("session_id");
    if (!sid) {
      sid = Math.random().toString(36).substring(2, 10);
      sessionStorage.setItem("session_id", sid);
    }
    return sid;
  };

  useEffect(() => {
    fetchEda();
  }, []);

  const fetchEda = async () => {
    setLoadingEda(true);
    try {
      const res = await axios.get(`${API_BASE}/eda?session_id=${getSessionId()}`);
      setEdaData(res.data);
    } catch (e) {
      console.error(e);
    }
    setLoadingEda(false);
  };

  const runAbTest = async () => {
    setLoadingAb(true);
    try {
      const res = await axios.post(`${API_BASE}/ab_test?session_id=${getSessionId()}`, { lift_pp: parseFloat(liftInput) });
      setAbResult(res.data);
    } catch (e) {
      console.error(e);
    }
    setLoadingAb(false);
  };

  const runPredict = async () => {
    setLoadingPred(true);
    try {
      const res = await axios.post(`${API_BASE}/predict?session_id=${getSessionId()}`, {
        order_value: parseFloat(predForm.order_value),
        installments: parseInt(predForm.installments),
        review_score: parseInt(predForm.review_score),
        was_late: parseInt(predForm.was_late),
        payment_type: predForm.payment_type
      });
      setPredResult(res.data.probability_repeat);
    } catch (e) {
      console.error(e);
    }
    setLoadingPred(false);
  };

  const handleUpload = async () => {
    if (!uploadFiles || uploadFiles.length === 0) return;
    setLoadingUpload(true);
    setUploadResult(null);
    try {
      const formData = new FormData();
      for (const file of uploadFiles) {
        formData.append('files', file);
      }
      const res = await axios.post(`${API_BASE}/upload?session_id=${getSessionId()}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setUploadResult(res.data);
      if (res.data.success) {
        // Refresh the dashboard data
        fetchEda();
      }
    } catch (e) {
      setUploadResult({ success: false, errors: [e.message] });
    }
    setLoadingUpload(false);
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-4 md:px-8 py-4 flex flex-col md:flex-row items-center justify-between sticky top-0 z-50 shadow-sm">
        <div className="flex items-center space-x-3 w-full md:w-auto">
          <div className="bg-blue-600 p-2 rounded-lg text-white">
            <Activity size={24} />
          </div>
          <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-700 to-indigo-700">
            RetailPulse
          </h1>
        </div>
        <div className="flex overflow-x-auto space-x-4 md:space-x-6 w-full md:w-auto mt-4 md:mt-0 pb-1 hide-scrollbar">
          <button onClick={() => setActiveTab("overview")} className={`font-medium whitespace-nowrap pb-1 ${activeTab === 'overview' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-slate-500 hover:text-slate-900'}`}>Overview</button>
          <button onClick={() => setActiveTab("ab_test")} className={`font-medium pb-1 ${activeTab === 'ab_test' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-slate-500 hover:text-slate-900'}`}>A/B Test</button>
          <button onClick={() => setActiveTab("predict")} className={`font-medium whitespace-nowrap pb-1 ${activeTab === 'predict' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-slate-500 hover:text-slate-900'}`}>Predictor</button>
          <button onClick={() => setActiveTab("upload")} className={`font-medium whitespace-nowrap pb-1 ${activeTab === 'upload' ? 'text-emerald-600 border-b-2 border-emerald-600' : 'text-slate-500 hover:text-slate-900'}`}>Upload Data</button>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 md:px-8 py-6 md:py-8">
        {activeTab === "overview" && (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {loadingEda && <p className="text-slate-500 animate-pulse flex items-center justify-center py-20 text-lg">Loading analytics...</p>}
            {!loadingEda && !edaData && (
              <div className="flex flex-col items-center justify-center p-12 bg-white rounded-2xl shadow-sm border border-slate-200 mt-10">
                <AlertCircle className="w-16 h-16 text-slate-300 mb-6" />
                <h3 className="text-2xl font-semibold text-slate-800">No Analytics Data Found</h3>
                <p className="text-slate-500 mt-3 text-center max-w-lg leading-relaxed">
                  The dashboard is currently empty. Please go to the <strong className="text-slate-700">Upload Data</strong> tab and upload your CSV files to populate the database and unlock insights!
                </p>
                <button onClick={() => setActiveTab("upload")} className="mt-8 px-6 py-3 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 font-medium transition-colors shadow-sm">
                  Go to Upload Data
                </button>
              </div>
            )}
            {edaData && (
              <>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between hover:shadow-md transition-shadow">
                    <div>
                      <p className="text-sm font-semibold text-slate-500 uppercase tracking-wide">Total Revenue</p>
                      <p className="text-3xl font-bold mt-1 text-slate-800">R$ {edaData.metrics.total_revenue.toLocaleString(undefined, {maximumFractionDigits:0})}</p>
                    </div>
                    <div className="h-12 w-12 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center">
                      <ShoppingCart size={24} />
                    </div>
                  </div>
                  <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between hover:shadow-md transition-shadow">
                    <div>
                      <p className="text-sm font-semibold text-slate-500 uppercase tracking-wide">Repeat Rate</p>
                      <p className="text-3xl font-bold mt-1 text-slate-800">{edaData.metrics.repeat_rate.toFixed(1)}%</p>
                    </div>
                    <div className="h-12 w-12 bg-indigo-50 text-indigo-600 rounded-full flex items-center justify-center">
                      <Users size={24} />
                    </div>
                  </div>
                  <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between hover:shadow-md transition-shadow">
                    <div>
                      <p className="text-sm font-semibold text-slate-500 uppercase tracking-wide">Late Delivery Rate</p>
                      <p className="text-3xl font-bold mt-1 text-slate-800">{edaData.metrics.late_rate.toFixed(1)}%</p>
                    </div>
                    <div className="h-12 w-12 bg-rose-50 text-rose-600 rounded-full flex items-center justify-center">
                      <LineChart size={24} />
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                  <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                    <h3 className="text-lg font-bold mb-4">Repeat Rate by State</h3>
                    <div className="h-[300px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={edaData.repeat_rate_by_state.slice(0, 15)}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} />
                          <XAxis dataKey="state" />
                          <YAxis />
                          <Tooltip />
                          <Bar dataKey="is_repeat_customer" fill="#3b82f6" radius={[4, 4, 0, 0]} name="Repeat Rate (%)" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                  
                  <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                    <h3 className="text-lg font-bold mb-4">Avg Review Score (Late vs On-time)</h3>
                    <div className="h-[300px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={edaData.review_by_delivery}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} />
                          <XAxis dataKey="delivery" />
                          <YAxis domain={[0, 5]} />
                          <Tooltip />
                          <Bar dataKey="review_score" fill="#8b5cf6" radius={[4, 4, 0, 0]} name="Review Score" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {activeTab === "ab_test" && (
          <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm">
              <div className="flex items-center space-x-3 mb-6">
                <Target className="text-indigo-600" size={28} />
                <h2 className="text-2xl font-bold">A/B Testing Simulator</h2>
              </div>
              <p className="text-slate-600 mb-6">Simulate offering a 10% discount on the 2nd purchase to a random half of the customers.</p>
              
              <div className="mb-6">
                <label className="block text-sm font-medium text-slate-700 mb-2">Simulated Promo Lift (Percentage Points)</label>
                <div className="flex items-center space-x-4">
                  <input 
                    type="range" min="0" max="10" step="0.5" 
                    value={liftInput} onChange={e => setLiftInput(e.target.value)}
                    className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                  />
                  <span className="font-bold w-12 text-right">{liftInput}</span>
                </div>
              </div>
              
              <button onClick={runAbTest} disabled={loadingAb} className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-3 rounded-lg font-medium flex items-center transition-colors">
                {loadingAb ? "Running Simulation..." : <><Play size={18} className="mr-2" /> Run Simulation</>}
              </button>
            </div>

            {abResult && (
              <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm space-y-6">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pb-6 border-b border-slate-100">
                  <div>
                    <p className="text-sm text-slate-500">Treatment Rate</p>
                    <p className="text-xl font-bold">{(abResult.treatment_rate*100).toFixed(2)}%</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Control Rate</p>
                    <p className="text-xl font-bold">{(abResult.control_rate*100).toFixed(2)}%</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Absolute Lift</p>
                    <p className="text-xl font-bold text-emerald-600">+{abResult.absolute_lift_pp.toFixed(2)}pp</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">p-value</p>
                    <p className="text-xl font-bold">{abResult.p_val.toFixed(4)}</p>
                  </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
                  <div className="bg-slate-50 p-6 rounded-xl border border-slate-100">
                    <p className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-1">Modeled Incremental Rev</p>
                    <p className="text-2xl font-bold text-emerald-600">R$ {abResult.incremental_revenue.toLocaleString(undefined, {maximumFractionDigits:0})}</p>
                  </div>
                  <div className="bg-slate-50 p-6 rounded-xl border border-slate-100">
                    <p className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-1">Modeled Discount Cost</p>
                    <p className="text-2xl font-bold text-rose-600">R$ {abResult.discount_cost.toLocaleString(undefined, {maximumFractionDigits:0})}</p>
                  </div>
                </div>
                
                <div className={`p-4 rounded-lg font-medium text-center ${abResult.recommend_ship ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'}`}>
                  {abResult.recommend_ship 
                    ? "🚀 RECOMMENDATION: SHIP. Lift is significant and ROI is positive." 
                    : "✋ RECOMMENDATION: DO NOT SHIP AS-IS. Cost exceeds benefit or non-significant."}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === "predict" && (
          <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm">
              <h2 className="text-2xl font-bold mb-2">Repeat Purchase Predictor</h2>
              <p className="text-slate-600 mb-6">Simulate a first order to predict if the customer will return.</p>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Order Value (R$)</label>
                  <input type="number" value={predForm.order_value} onChange={(e) => setPredForm({...predForm, order_value: e.target.value})} className="w-full border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Installments</label>
                  <input type="number" value={predForm.installments} onChange={(e) => setPredForm({...predForm, installments: e.target.value})} className="w-full border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Review Score (1-5)</label>
                  <input type="number" min="1" max="5" value={predForm.review_score} onChange={(e) => setPredForm({...predForm, review_score: e.target.value})} className="w-full border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Was Late?</label>
                  <select value={predForm.was_late} onChange={(e) => setPredForm({...predForm, was_late: e.target.value})} className="w-full border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all">
                    <option value={0}>No (On-time)</option>
                    <option value={1}>Yes (Late)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Payment Type</label>
                  <select value={predForm.payment_type} onChange={(e) => setPredForm({...predForm, payment_type: e.target.value})} className="w-full border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all">
                    <option value="credit_card">Credit Card</option>
                    <option value="boleto">Boleto</option>
                    <option value="voucher">Voucher</option>
                    <option value="debit_card">Debit Card</option>
                    <option value="unknown">Unknown</option>
                  </select>
                </div>
              </div>
              
              <button onClick={runPredict} disabled={loadingPred} className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium w-full md:w-auto transition-colors shadow-sm">
                {loadingPred ? "Predicting..." : "Predict Customer Outcome"}
              </button>
            </div>
            
            {predResult !== null && (
              <div className="bg-gradient-to-br from-blue-900 to-indigo-900 text-white p-8 rounded-2xl shadow-lg text-center transform hover:scale-[1.02] transition-transform">
                <p className="text-blue-200 font-medium tracking-wide uppercase text-sm mb-2">Probability of Repeat Purchase</p>
                <div className="text-6xl font-bold text-white drop-shadow-sm">
                  {(predResult * 100).toFixed(1)}%
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === "upload" && (
          <div className="max-w-4xl mx-auto space-y-8">
            <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm">
              <div className="flex items-center space-x-3 mb-6">
                <Upload className="text-emerald-600" size={28} />
                <h2 className="text-2xl font-bold">Upload Custom Data</h2>
              </div>
              <p className="text-slate-600 mb-2">Upload your own CSV files to replace the demo data and run the full analytics pipeline on your dataset.</p>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6">
                <p className="text-sm text-slate-500">Required files (5 CSVs): <code className="bg-slate-100 px-1.5 py-0.5 rounded text-xs">orders</code>, <code className="bg-slate-100 px-1.5 py-0.5 rounded text-xs">customers</code>, <code className="bg-slate-100 px-1.5 py-0.5 rounded text-xs">order_items</code>, <code className="bg-slate-100 px-1.5 py-0.5 rounded text-xs">payments</code>, <code className="bg-slate-100 px-1.5 py-0.5 rounded text-xs">reviews</code></p>
                <a href="/sample_data.zip" download className="mt-3 sm:mt-0 inline-flex items-center text-sm font-medium text-emerald-600 bg-emerald-50 px-3 py-1.5 rounded hover:bg-emerald-100 transition-colors">
                  Download Sample CSVs
                </a>
              </div>
              {/* Drop Zone */}
              <div
                className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all ${dragOver ? 'border-emerald-500 bg-emerald-50' : 'border-slate-300 hover:border-slate-400 bg-slate-50'}`}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragOver(false);
                  setUploadFiles(Array.from(e.dataTransfer.files));
                  setUploadResult(null);
                }}
                onClick={() => document.getElementById('file-input').click()}
              >
                <Upload className="mx-auto text-slate-400 mb-3" size={40} />
                <p className="text-slate-600 font-medium">Drag & drop your CSV files here</p>
                <p className="text-sm text-slate-400 mt-1">or click to browse</p>
                <input
                  id="file-input"
                  type="file"
                  multiple
                  accept=".csv"
                  className="hidden"
                  onChange={(e) => {
                    setUploadFiles(Array.from(e.target.files));
                    setUploadResult(null);
                  }}
                />
              </div>

              {/* Selected Files */}
              {uploadFiles && uploadFiles.length > 0 && (
                <div className="mt-6 space-y-2">
                  <p className="text-sm font-semibold text-slate-700">{uploadFiles.length} file(s) selected:</p>
                  {uploadFiles.map((f, i) => (
                    <div key={i} className="flex items-center justify-between bg-slate-50 px-4 py-2 rounded-lg border border-slate-100">
                      <span className="text-sm text-slate-700">{f.name}</span>
                      <span className="text-xs text-slate-400">{(f.size / 1024).toFixed(0)} KB</span>
                    </div>
                  ))}
                  <button onClick={handleUpload} disabled={loadingUpload} className="mt-4 bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-3 rounded-lg font-medium w-full transition-colors shadow-sm">
                    {loadingUpload ? "Uploading & Processing..." : "Upload & Process Data"}
                  </button>
                </div>
              )}
            </div>

            {/* Upload Result */}
            {uploadResult && (
              <div className={`p-6 rounded-2xl border shadow-sm ${uploadResult.success ? 'bg-emerald-50 border-emerald-200' : 'bg-rose-50 border-rose-200'}`}>
                <div className="flex items-center space-x-3 mb-3">
                  {uploadResult.success
                    ? <CheckCircle className="text-emerald-600" size={24} />
                    : <AlertCircle className="text-rose-600" size={24} />
                  }
                  <h3 className={`text-lg font-bold ${uploadResult.success ? 'text-emerald-800' : 'text-rose-800'}`}>
                    {uploadResult.success ? "Upload Successful!" : "Upload Failed"}
                  </h3>
                </div>
                {uploadResult.message && <p className="text-emerald-700 mb-2">{uploadResult.message}</p>}
                {uploadResult.errors && uploadResult.errors.length > 0 && (
                  <ul className="list-disc list-inside space-y-1">
                    {uploadResult.errors.map((err, i) => (
                      <li key={i} className="text-sm text-rose-700">{err}</li>
                    ))}
                  </ul>
                )}
                {uploadResult.success && (
                  <p className="text-sm text-emerald-600 mt-3">Dashboard data has been refreshed. Switch to the <button onClick={() => setActiveTab("overview")} className="underline font-semibold">Overview</button> tab to see your new data!</p>
                )}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
