import React, { useMemo, useState } from 'react';
import { Search, ZoomIn, ZoomOut, Maximize2, User, Loader2 } from 'lucide-react';
import { 
  DndContext, 
  useDraggable, 
  useDroppable,
  PointerSensor,
  useSensor,
  useSensors,
  DragOverlay
} from '@dnd-kit/core';
import { CSS } from '@dnd-kit/utilities';

const DEPT_COLORS = {
  'BSC': 'bg-blue-500',
  'BCOM': 'bg-green-500',
  'BA': 'bg-orange-500',
  'BCA': 'bg-purple-500',
  'BBA': 'bg-pink-500',
  'DEFAULT': 'bg-slate-400'
};

const DraggableSeatContent = ({ seat, isHighlighted, isDragging }) => {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({
    id: `student-${seat.student_id || seat.reg_no}`,
    data: seat
  });

  const style = {
    transform: CSS.Translate.toString(transform),
  };

  const deptColor = DEPT_COLORS[seat?.program] || DEPT_COLORS['DEFAULT'];

  return (
    <div 
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className={`relative w-28 h-36 rounded-xl border-2 transition-all duration-300 flex flex-col items-center justify-center p-2 text-center group cursor-grab active:cursor-grabbing ${
        isDragging ? 'opacity-40 grayscale' : ''
      } ${
        isHighlighted 
          ? 'border-indigo-600 ring-4 ring-indigo-500/20 shadow-lg scale-105 z-10' 
          : 'border-slate-100 bg-white hover:border-slate-300 hover:shadow-md'
      }`}
    >
      <div className={`w-10 h-10 rounded-full ${deptColor} flex items-center justify-center text-white mb-2 shadow-sm transition-transform group-hover:scale-110`}>
        <User className="w-5 h-5" />
      </div>
      <div className="w-full truncate px-1">
        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter mb-0.5">{seat.reg_no}</p>
        <p className="text-[11px] font-bold text-slate-900 leading-tight truncate">{seat.student_name}</p>
        <p className={`text-[9px] font-bold mt-1 inline-block px-1.5 py-0.5 rounded text-white ${deptColor}`}>
          {seat.program}
        </p>
      </div>
      
      {!isDragging && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-3 bg-slate-900 text-white text-xs rounded-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-20 shadow-xl">
          <p className="font-bold">{seat.student_name}</p>
          <p className="text-slate-400">USN: {seat.reg_no}</p>
          <p className="text-slate-400">Dept: {seat.program}</p>
          <p className="text-indigo-400 font-bold mt-1">{seat.seat_pos}</p>
        </div>
      )}
    </div>
  );
};

const DroppableSeat = ({ seatPos, row, children, isOccupied }) => {
  const { isOver, setNodeRef } = useDroppable({
    id: `seat-${row}-${seatPos}`,
    data: { row, seatPos }
  });

  return (
    <div 
      ref={setNodeRef}
      className={`relative rounded-xl transition-all duration-200 ${
        isOver && !isOccupied ? 'ring-4 ring-emerald-500 ring-inset bg-emerald-50' : ''
      } ${
        isOver && isOccupied ? 'ring-4 ring-rose-500 ring-inset bg-rose-50' : ''
      }`}
    >
      {children}
    </div>
  );
};

const EmptySeat = () => (
  <div className="w-28 h-36 rounded-xl border-2 border-dashed border-slate-100 bg-slate-50/50 flex items-center justify-center">
    <div className="w-2 h-2 rounded-full bg-slate-200"></div>
  </div>
);

const SeatMap = ({ room, assignments = [], onMove }) => {
  const [zoom, setZoom] = useState(1);
  const [search, setSearch] = useState('');
  const [activeId, setActiveId] = useState(null);
  const [moving, setMoving] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  const grid = useMemo(() => {
    const rows = room.rows;
    const layout = room.column_layout || [3, 2, 3];
    const aisles = room.aisle_after_column || (room.column_layout ? [] : [0, 1]);
    const result = [];

    for (let r = 1; r <= rows; r++) {
      const rowData = [];
      let visualCol = 1;
      layout.forEach((count, blockIdx) => {
        const block = [];
        for (let c = 0; c < count; c++) {
          const seatPosStr = `R${r}C${visualCol}`;
          const seatData = assignments.find(a => a.row === r && (a.seat_pos === seatPosStr || a.seat_position === seatPosStr));
          block.push({ pos: seatPosStr, data: seatData });
          visualCol++;
        }
        rowData.push(block);
        if (aisles.includes(blockIdx)) {
          visualCol++; // Skip for aisle
        }
      });
      result.push(rowData);
    }
    return result;
  }, [room, assignments]);


  const handleDragStart = (event) => {
    setActiveId(event.active.id);
  };

  const handleDragEnd = async (event) => {
    setActiveId(null);
    const { active, over } = event;

    if (over && active.id !== over.id) {
      const student = active.data.current;
      const target = over.data.current;

      setMoving(true);
      try {
        await onMove(student, target);
      } finally {
        setMoving(false);
      }
    }
  };

  const activeSeat = useMemo(() => {
    if (!activeId) return null;
    return assignments.find(a => `student-${a.student_id || a.reg_no}` === activeId);
  }, [activeId, assignments]);

  return (
    <DndContext 
      sensors={sensors}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="flex flex-col h-full space-y-6 relative">
        {moving && (
          <div className="absolute inset-0 z-50 bg-white/20 backdrop-blur-[2px] flex items-center justify-center rounded-3xl">
            <div className="bg-white p-4 rounded-2xl shadow-xl flex items-center gap-3">
              <Loader2 className="w-6 h-6 text-indigo-600 animate-spin" />
              <span className="font-bold text-slate-900">Updating Seats...</span>
            </div>
          </div>
        )}

        {/* Controls (same as before) */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-4 rounded-2xl border border-slate-100 shadow-sm">
          <div className="flex items-center gap-4">
            <div className="flex items-center bg-slate-100 rounded-xl p-1">
              <button onClick={() => setZoom(prev => Math.max(prev - 0.1, 0.5))} className="p-2 hover:bg-white rounded-lg transition-all text-slate-600"><ZoomOut className="w-4 h-4" /></button>
              <span className="px-3 text-xs font-bold text-slate-500 w-12 text-center">{Math.round(zoom * 100)}%</span>
              <button onClick={() => setZoom(prev => Math.min(prev + 0.1, 2))} className="p-2 hover:bg-white rounded-lg transition-all text-slate-600"><ZoomIn className="w-4 h-4" /></button>
            </div>
            <button onClick={() => setZoom(1)} className="p-3 bg-slate-100 hover:bg-slate-200 rounded-xl transition-colors text-slate-600"><Maximize2 className="w-4 h-4" /></button>
          </div>
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5" />
            <input type="text" placeholder="Search student..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-full pl-12 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl focus:ring-2 focus:ring-indigo-500/20 outline-none transition-all" />
          </div>
          <div className="flex items-center gap-4 px-2">
            {Object.entries(DEPT_COLORS).filter(([k]) => k !== 'DEFAULT').map(([dept, color]) => (
              <div key={dept} className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${color}`}></div>
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">{dept}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Map Container */}
        <div className="flex-1 bg-slate-100 rounded-3xl overflow-auto border-4 border-white shadow-inner p-12 min-h-[600px]">
          <div 
            className="inline-block transition-transform duration-300 origin-top-left"
            style={{ transform: `scale(${zoom})` }}
          >
            <div className="space-y-12">
              {grid.map((row, rIdx) => (
                <div key={rIdx} className="flex items-center gap-4">
                  <div className="w-10 h-10 bg-white rounded-full flex items-center justify-center shadow-sm border border-slate-200 text-slate-400 font-bold text-xs">{rIdx + 1}</div>
                  <div className="flex gap-12">
                    {row.map((block, bIdx) => (
                      <div key={bIdx} className="flex gap-3">
                        {block.map((seatSlot, sIdx) => (
                          <DroppableSeat 
                            key={sIdx} 
                            row={rIdx + 1} 
                            seatPos={seatSlot.pos}
                            isOccupied={!!seatSlot.data}
                          >
                            {seatSlot.data ? (
                              <DraggableSeatContent 
                                seat={seatSlot.data} 
                                isHighlighted={search && seatSlot.data.student_name.toLowerCase().includes(search.toLowerCase())}
                                isDragging={activeId === `student-${seatSlot.data.student_id || seatSlot.data.reg_no}`}
                              />
                            ) : (
                              <EmptySeat />
                            )}
                          </DroppableSeat>
                        ))}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-16 w-full py-4 bg-white/50 border-2 border-dashed border-slate-300 rounded-3xl flex items-center justify-center text-slate-400 font-bold uppercase tracking-[1em]">
              Front of Room
            </div>
          </div>
        </div>

        {/* Drag Overlay for smooth visuals */}
        <DragOverlay>
          {activeSeat ? (
            <div className="scale-105 opacity-80 cursor-grabbing">
               <div className={`relative w-28 h-36 rounded-xl border-2 border-indigo-600 bg-white shadow-2xl flex flex-col items-center justify-center p-2 text-center`}>
                  <div className={`w-10 h-10 rounded-full ${DEPT_COLORS[activeSeat.program] || DEPT_COLORS.DEFAULT} flex items-center justify-center text-white mb-2 shadow-sm`}>
                    <User className="w-5 h-5" />
                  </div>
                  <div className="w-full truncate px-1">
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter mb-0.5">{activeSeat.reg_no}</p>
                    <p className="text-[11px] font-bold text-slate-900 leading-tight truncate">{activeSeat.student_name}</p>
                  </div>
               </div>
            </div>
          ) : null}
        </DragOverlay>
      </div>
    </DndContext>
  );
};

export default SeatMap;
