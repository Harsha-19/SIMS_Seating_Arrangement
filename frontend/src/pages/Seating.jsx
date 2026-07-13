import React, { useEffect, useState } from 'react';
import { 
  Grid3X3, 
  Zap,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ChevronRight,
  Eye,
  Download
} from 'lucide-react';
import { seatingApi, examScheduleApi, roomApi, normalizeArrayResponse } from '../api';
import SeatMap from '../components/SeatMap';

const Seating = () => {
  const [exams, setExams] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [generatedData, setGeneratedData] = useState(null);
  const [viewMode, setViewMode] = useState('form'); // 'form' or 'map'
  const [selectedRoomIdx, setSelectedRoomIdx] = useState(0);

  // Form state
  const [selectedExam, setSelectedExam] = useState('');
  const [selectedRooms, setSelectedRooms] = useState([]);

  const fetchData = async () => {
    try {
      const [examsData, roomsData] = await Promise.all([
        examScheduleApi.getExamSchedules(),
        roomApi.getRooms()
      ]);
      setExams(normalizeArrayResponse(examsData, ['results', 'data', 'examSchedules', 'exams']));
      setRooms(normalizeArrayResponse(roomsData, ['results', 'data', 'rooms']));
    } catch (err) {
      setError('Failed to load required data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleGenerate = async (e) => {
    e.preventDefault();
    if (!selectedExam || selectedRooms.length === 0) {
      setError('Please select an exam and at least one room.');
      return;
    }

    setGenerating(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await seatingApi.generateSeating({
        exam_id: selectedExam,
        room_ids: selectedRooms
      });
      setGeneratedData(response.data || response);
      setSuccess(`Success! ${response.message || 'Seating generated.'}`);
      setViewMode('map');
    } catch (err) {
      console.error("Seating generation failed:", err);
      const responseData = err?.response?.data;

      let message =
        responseData?.error ||
        responseData?.message ||
        "Failed to generate seating";

      if (responseData?.details?.shortage) {
        message = `${message} ${responseData.details.students} students cannot fit into ${responseData.details.capacity} seats.`;
      }

      setError(message);
    } finally {
      setGenerating(false);
    }
  };

  const handleMoveSeat = async (student, target) => {
    setError(null);
    setSuccess(null);
    
    try {
      const planId = generatedData.plan.id;
      const response = await seatingApi.move(planId, {
        student_id: student.student_id || student.reg_no,
        target_room_id: generatedData.rooms[selectedRoomIdx].room_id, // For now assuming same room moves
        row: target.row,
        seat_pos: target.seatPos
      });

      // Update local state for immediate feedback
      const updatedRooms = [...generatedData.rooms];
      const currentRoom = { ...updatedRooms[selectedRoomIdx] };
      const currentAssignments = [...currentRoom.assignments];
      
      const studentIdx = currentAssignments.findIndex(a => a.reg_no === student.reg_no);
      if (studentIdx !== -1) {
        currentAssignments[studentIdx] = {
          ...currentAssignments[studentIdx],
          row: target.row,
          seat_pos: target.seatPos
        };
        currentRoom.assignments = currentAssignments;
        updatedRooms[selectedRoomIdx] = currentRoom;
        setGeneratedData({ ...generatedData, rooms: updatedRooms });
      }

      if (response.warnings?.length > 0) {
        setError(`Warning: ${response.warnings.join(', ')}`);
      } else {
        setSuccess('Seat updated successfully.');
      }
    } catch (err) {
      setError(typeof err === 'string' ? err : 'Failed to move seat.');
      console.error(err);
    }
  };

  const toggleRoom = (id) => {
    setSelectedRooms(prev => 
      prev.includes(id) ? prev.filter(r => r !== id) : [...prev, id]
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
      </div>
    );
  }

  if (viewMode === 'map' && generatedData && Array.isArray(generatedData.rooms) && generatedData.rooms.length > 0) {
    const currentRoomData = generatedData.rooms[selectedRoomIdx] || generatedData.rooms[0];
    const roomInfo = Array.isArray(rooms) ? rooms.find(r => r.id === currentRoomData?.room_id) : null;

    return (
      <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => setViewMode('form')}
              className="p-2 hover:bg-slate-100 rounded-lg transition-colors text-slate-500"
            >
              <ChevronRight className="w-6 h-6 rotate-180" />
            </button>
            <div>
              <h2 className="text-3xl font-bold text-slate-900 tracking-tight">
                Layout Editor
              </h2>
              <p className="text-slate-500 mt-1">
                Drag and drop students to rearrange seats manually.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button 
              onClick={async () => {
                try {
                  const blob = await seatingApi.exportExcel(generatedData.plan.id);
                  const url = window.URL.createObjectURL(new Blob([blob]));
                  const link = document.createElement('a');
                  link.href = url;
                  link.setAttribute('download', `Seating_Plan_${generatedData.plan.id}.xlsx`);
                  document.body.appendChild(link);
                  link.click();
                  link.remove();
                } catch (err) {
                  alert('Export failed.');
                }
              }}
              className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-xl font-bold text-slate-600 hover:bg-slate-50 transition-all shadow-sm"
            >
              <Download className="w-4 h-4" />
              Export
            </button>

            <button className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-xl font-bold hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-500/20">
              <CheckCircle2 className="w-4 h-4" />
              Publish Plan
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-amber-50 border border-amber-100 text-amber-600 p-4 rounded-xl flex items-center gap-3 animate-in fade-in slide-in-from-top-2">
            <AlertCircle className="w-5 h-5" />
            <p className="text-sm font-bold">{error}</p>
          </div>
        )}

        <div className="flex items-center gap-2 overflow-x-auto pb-2">
          {Array.isArray(generatedData?.rooms) && generatedData.rooms.map((room, idx) => (
            <button
              key={room.room_id}
              onClick={() => setSelectedRoomIdx(idx)}
              className={`px-6 py-3 rounded-xl font-bold whitespace-nowrap transition-all border-2 ${
                selectedRoomIdx === idx
                  ? 'bg-indigo-600 text-white border-indigo-600 shadow-lg shadow-indigo-500/20'
                  : 'bg-white text-slate-500 border-transparent hover:border-slate-200'
              }`}
            >
              Room {room.room_number} ({room.students_seated} Seats)
            </button>
          ))}
        </div>

        <div className="h-[calc(100vh-320px)]">
          <SeatMap 
            room={roomInfo} 
            assignments={currentRoomData.assignments} 
            onMove={handleMoveSeat}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Generate Seating</h2>
          <p className="text-slate-500 mt-1">Select an exam and rooms to create an optimized layout.</p>
        </div>
        {generatedData && (
          <button 
            onClick={() => setViewMode('map')}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-xl font-bold text-slate-600 hover:bg-slate-50 transition-all shadow-sm"
          >
            <Eye className="w-4 h-4" />
            Last Result
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <form onSubmit={handleGenerate} className="bg-white p-8 rounded-2xl shadow-sm border border-slate-100 space-y-6">
          <div className="space-y-2">
            <label className="text-sm font-bold text-slate-700 uppercase tracking-wider">Select Exam</label>
            <select 
              value={selectedExam}
              onChange={(e) => setSelectedExam(e.target.value)}
              className="w-full p-4 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
            >
              <option value="">Choose an exam...</option>
              {Array.isArray(exams) && exams.length > 0 ? (
                exams.map(exam => (
                  <option key={exam.id} value={exam.id}>
                    {exam.subject_info?.subject_name} ({new Date(exam.exam_date).toLocaleDateString()})
                  </option>
                ))
              ) : (
                <option value="" disabled>No exams available</option>
              )}
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-bold text-slate-700 uppercase tracking-wider">Select Rooms</label>
            <div className="grid grid-cols-2 gap-3">
              {Array.isArray(rooms) && rooms.length > 0 ? (
                rooms.map(room => (
                  <button
                    key={room.id}
                    type="button"
                    onClick={() => toggleRoom(room.id)}
                    className={`p-4 rounded-xl border-2 transition-all text-left flex items-center justify-between ${
                      selectedRooms.includes(room.id)
                        ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
                        : 'border-slate-100 bg-slate-50 text-slate-500 hover:border-slate-200'
                    }`}
                  >
                    <span className="font-bold">{room.room_number}</span>
                    {selectedRooms.includes(room.id) && <CheckCircle2 className="w-5 h-5" />}
                  </button>
                ))
              ) : (
                <div className="col-span-2 text-sm text-slate-500 p-4 text-center border-2 border-dashed border-slate-200 rounded-xl">
                  No rooms available
                </div>
              )}
            </div>
          </div>

          {error && (
            <div className="p-4 bg-red-50 text-red-600 rounded-xl flex items-center gap-3 text-sm font-medium border border-red-100">
              <AlertCircle className="w-5 h-5 shrink-0" />
              {error}
            </div>
          )}

          {success && (
            <div className="p-4 bg-emerald-50 text-emerald-600 rounded-xl flex items-center gap-3 text-sm font-medium border border-emerald-100">
              <CheckCircle2 className="w-5 h-5 shrink-0" />
              {success}
            </div>
          )}

          <button
            type="submit"
            disabled={generating}
            className="w-full py-4 bg-indigo-600 text-white rounded-xl font-bold text-lg hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-500/20 flex items-center justify-center gap-3 disabled:opacity-50"
          >
            {generating ? (
              <>
                <Loader2 className="w-6 h-6 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Zap className="w-6 h-6" />
                Generate Plan
              </>
            )}
          </button>
        </form>

        <div className="space-y-6">
          <div className="bg-slate-900 p-8 rounded-2xl shadow-xl text-white">
            <h3 className="text-xl font-bold mb-4">Guidelines</h3>
            <ul className="space-y-4 text-slate-400">
              <li className="flex gap-3">
                <ChevronRight className="text-indigo-500 w-5 h-5 shrink-0" />
                Select at least one room with sufficient total capacity for the students.
              </li>
              <li className="flex gap-3">
                <ChevronRight className="text-indigo-500 w-5 h-5 shrink-0" />
                The system will optimize seating to minimize cheating risks.
              </li>
            </ul>
          </div>
          
          <div className="p-8 border-2 border-dashed border-slate-200 rounded-2xl flex flex-col items-center justify-center text-center">
            <div className="p-4 bg-slate-50 rounded-full mb-4">
              <Grid3X3 className="w-8 h-8 text-slate-300" />
            </div>
            <h4 className="font-bold text-slate-900">Preview Layout</h4>
            <p className="text-slate-500 text-sm mt-2">Generate a plan to see the visual layout preview here.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Seating;
