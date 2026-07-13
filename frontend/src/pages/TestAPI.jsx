import { useState } from "react";
import { generateSeating } from "../api/seating";

export default function TestAPI() {
  const [result, setResult] = useState(null);
  const [examId, setExamId] = useState(1);
  const [roomIds, setRoomIds] = useState("26"); // Defaulting to the one just created
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    setLoading(true);
    setResult(null);
    try {
      const data = await generateSeating({
        exam_id: parseInt(examId),
        room_ids: roomIds.split(',').map(id => parseInt(id.trim())),
        preview_only: true,
      });
      setResult(data);
    } catch (err) {
      console.error(err);
      setResult(err.response?.data || { error: err.message || "Request failed" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-100">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">API Connection Tester</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="space-y-2">
            <label className="text-sm font-bold text-slate-500 uppercase">Exam ID</label>
            <input 
              type="number" 
              value={examId}
              onChange={(e) => setExamId(e.target.value)}
              className="w-full p-4 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 outline-none"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-bold text-slate-500 uppercase">Room IDs (comma separated)</label>
            <input 
              type="text" 
              value={roomIds}
              onChange={(e) => setRoomIds(e.target.value)}
              className="w-full p-4 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 outline-none"
              placeholder="e.g. 1, 2, 3"
            />
          </div>
        </div>

        <button
          onClick={handleClick}
          disabled={loading}
          className="w-full bg-indigo-600 text-white py-4 rounded-xl font-bold text-lg hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-500/20 flex items-center justify-center gap-3 disabled:opacity-50"
        >
          {loading ? (
            <span className="animate-pulse">Testing Connection...</span>
          ) : (
            "Run Seating Generation Test"
          )}
        </button>
      </div>

      {result && (
        <div className="space-y-4">
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider ml-2">Response Output</h3>
          <pre className={`p-8 rounded-2xl overflow-auto max-h-[600px] text-xs font-mono shadow-inner border transition-all ${
            result.success === false ? 'bg-red-50 text-red-600 border-red-100' : 'bg-slate-900 text-emerald-400 border-slate-800'
          }`}>
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
