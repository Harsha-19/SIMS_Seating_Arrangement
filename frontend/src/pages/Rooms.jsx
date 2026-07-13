import React, { useEffect, useState } from 'react';
import { 
  DoorOpen, 
  Plus,
  AlertCircle,
  LayoutGrid,
  MoreVertical,
  Trash2
} from 'lucide-react';

import { roomApi, normalizeArrayResponse } from '../api';

const RoomCard = ({ room }) => (
  <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-all hover:-translate-y-1">
    <div className="flex items-start justify-between mb-4">
      <div className="p-3 rounded-xl bg-indigo-50 text-indigo-600">
        <DoorOpen className="w-6 h-6" />
      </div>
      <button 
        onClick={() => onDelete(room.id)}
        className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
      >
        <Trash2 className="w-5 h-5" />
      </button>
    </div>

    <div>
      <h3 className="text-xl font-bold text-slate-900">Room {room.room_number}</h3>
      <p className="text-slate-500 text-sm mt-1">{room.total_capacity} Seats Capacity</p>
    </div>
    <div className="mt-6 pt-6 border-t border-slate-50 flex items-center justify-between text-sm">
      <div className="flex items-center gap-2 text-slate-400 font-medium">
        <LayoutGrid className="w-4 h-4" />
        {room.rows} Rows
      </div>
      <span className="px-2 py-1 bg-emerald-50 text-emerald-600 rounded text-xs font-bold uppercase tracking-wider">
        Ready
      </span>
    </div>
  </div>
);

import Modal from '../components/Modal';
import { Loader2 } from 'lucide-react';

const Rooms = () => {
  const [rooms, setRooms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({ 
    room_number: '', 
    rows: 10, 
    left_seats: 3, 
    middle_seats: 4, 
    right_seats: 3 
  });

  const fetchRooms = async () => {
    setLoading(true);
    try {
      const data = await roomApi.getRooms();
      setRooms(normalizeArrayResponse(data, ['results', 'data', 'rooms']));
      setError(null);
    } catch (err) {
      setError('Failed to load rooms.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRooms();
  }, []);

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this room?')) return;
    try {
      await roomApi.delete(id);
      fetchRooms();
    } catch (err) {
      alert('Failed to delete room.');
    }
  };

  const handleSubmit = async (e) => {

    e.preventDefault();
    setIsSubmitting(true);
    try {
      await roomApi.create(formData);
      setIsModalOpen(false);
      setFormData({ room_number: '', rows: 10, left_seats: 3, middle_seats: 4, right_seats: 3 });
      fetchRooms();
    } catch (err) {
      alert('Failed to create room: ' + (err.response?.data?.message || err.message));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Rooms</h2>
          <p className="text-slate-500 mt-1">Configure examination halls and seat layouts.</p>
        </div>
        <button 
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-colors shadow-lg shadow-indigo-500/20"
        >
          <Plus className="w-4 h-4" />
          Add Room
        </button>
      </div>

      <Modal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)} 
        title="Add New Room"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-bold text-slate-700">Room Number / Name</label>
            <input
              required
              type="text"
              value={formData.room_number}
              onChange={(e) => setFormData({ ...formData, room_number: e.target.value })}
              placeholder="e.g. 101, LH-1"
              className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-bold text-slate-700">Total Rows</label>
              <input
                required
                type="number"
                value={formData.rows}
                onFocus={(e) => e.target.select()}
                onChange={(e) => setFormData({ ...formData, rows: parseInt(e.target.value) || 0 })}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
              />

            </div>
            <div className="space-y-2">
              <label className="text-sm font-bold text-slate-700">Left Column Seats</label>
              <input
                required
                type="number"
                value={formData.left_seats}
                onFocus={(e) => e.target.select()}
                onChange={(e) => setFormData({ ...formData, left_seats: parseInt(e.target.value) || 0 })}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
              />

            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-bold text-slate-700">Middle Column Seats</label>
              <input
                required
                type="number"
                value={formData.middle_seats}
                onFocus={(e) => e.target.select()}
                onChange={(e) => setFormData({ ...formData, middle_seats: parseInt(e.target.value) || 0 })}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
              />

            </div>
            <div className="space-y-2">
              <label className="text-sm font-bold text-slate-700">Right Column Seats</label>
              <input
                required
                type="number"
                value={formData.right_seats}
                onFocus={(e) => e.target.select()}
                onChange={(e) => setFormData({ ...formData, right_seats: parseInt(e.target.value) || 0 })}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
              />

            </div>
          </div>
          <button
            disabled={isSubmitting}
            type="submit"
            className="w-full py-4 bg-indigo-600 text-white rounded-2xl font-bold hover:bg-indigo-700 transition-all shadow-xl shadow-indigo-500/20 flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {isSubmitting ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Create Room'}
          </button>
        </form>
      </Modal>

      {error && (
        <div className="bg-red-50 border border-red-100 text-red-600 p-4 rounded-xl flex items-center gap-3">
          <AlertCircle className="w-5 h-5" />
          <p className="text-sm font-medium">{error}</p>
        </div>
      )}


      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map(i => (
            <div key={i} className="bg-white p-6 rounded-2xl border border-slate-100 h-48 animate-pulse">
              <div className="w-12 h-12 rounded-xl bg-slate-100 mb-4"></div>
              <div className="h-6 bg-slate-100 rounded w-1/2 mb-2"></div>
              <div className="h-4 bg-slate-100 rounded w-1/4"></div>
            </div>
          ))}
        </div>
      ) : Array.isArray(rooms) && rooms.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {rooms.map((room) => (
            <RoomCard key={room.id} room={room} onDelete={handleDelete} />
          ))}
        </div>

      ) : (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-12 text-center">
          <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4 text-slate-300">
            <DoorOpen className="w-8 h-8" />
          </div>
          <p className="text-slate-500 font-medium">No rooms configured.</p>
          <button 
            onClick={fetchRooms}
            className="text-indigo-600 text-sm font-bold mt-2 hover:underline"
          >
            Refresh data
          </button>
        </div>
      )}
    </div>
  );
};

export default Rooms;
