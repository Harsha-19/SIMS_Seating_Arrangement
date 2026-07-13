import React, { useState, useMemo, useCallback } from 'react';
import { 
  DndContext, 
  DragOverlay, 
  useDraggable, 
  useDroppable, 
  PointerSensor, 
  useSensor, 
  useSensors,
  defaultDropAnimationSideEffects
} from '@dnd-kit/core';
import { User, Layers, Info, AlertTriangle } from 'lucide-react';

const DEPT_COLORS = {
  'BSC': 'bg-blue-500 text-white border-blue-600',
  'BCOM': 'bg-green-500 text-white border-green-600',
  'BA': 'bg-orange-500 text-white border-orange-600',
  'BCA': 'bg-purple-500 text-white border-purple-600',
  'BBA': 'bg-pink-500 text-white border-pink-600',
};

const DEFAULT_COLOR = 'bg-slate-500 text-white border-slate-600';

const DraggableStudent = ({ student, isOverlay = false }) => {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `student-${student.student_id || student.reg_no}`,
    data: student,
  });

  const style = transform ? {
    transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`,
    zIndex: isOverlay ? 100 : undefined,
  } : undefined;

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className={`group relative h-full w-full rounded-xl border-2 transition-all duration-300 ease-out flex flex-col p-3 cursor-grab active:cursor-grabbing
        ${DEPT_COLORS[student.dept?.toUpperCase()] || DEFAULT_COLOR} 
        ${isDragging ? 'opacity-30 scale-95' : 'shadow-md shadow-black/20 hover:scale-[1.02] hover:-translate-y-0.5'}
        ${isOverlay ? 'shadow-2xl shadow-black/80 scale-105 border-white/50' : ''}
      `}
    >
      <div className="flex justify-between items-start mb-2">
        <span className="text-[10px] font-black opacity-40 uppercase tracking-tighter">
          R{student.row} C{student.col}
        </span>
        <div className="p-1 px-1.5 bg-black/20 rounded text-[10px] font-bold">
          SEM {student.semester}
        </div>
      </div>
      <div className="mt-auto">
        <h3 className="text-sm font-bold truncate leading-tight mb-1" title={student.student_name}>
          {student.student_name}
        </h3>
        <p className="text-[11px] font-medium opacity-80 flex items-center gap-1">
          {student.reg_no}
        </p>
      </div>
      {!isOverlay && (
        <div className="absolute inset-0 bg-black/60 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center justify-center pointer-events-none p-2">
          <Layers className="w-4 h-4 mr-2" />
          <span className="text-xs font-medium">Drag to Move</span>
        </div>
      )}
    </div>
  );
};

const DroppableSeat = ({ row, col, roomIdx, children, isOccupied }) => {
  const { isOver, setNodeRef } = useDroppable({
    id: `seat-${roomIdx}-${row}-${col}`,
    data: { row, col, roomIdx },
  });

  return (
    <div
      ref={setNodeRef}
      className={`h-28 rounded-xl border-2 transition-colors duration-200 
        ${isOver 
          ? 'bg-blue-500/20 border-blue-400 border-solid animate-pulse' 
          : isOccupied 
            ? 'border-transparent' 
            : 'bg-slate-800/30 border-slate-700/50 border-dashed hover:bg-slate-800/50 hover:border-slate-500'
        }
      `}
    >
      {children || (
        <div className="h-full w-full flex flex-col items-center justify-center gap-2 opacity-10">
          <Layers className="w-6 h-6" />
          <span className="text-[10px] font-bold uppercase tracking-widest">Vacant</span>
        </div>
      )}
    </div>
  );
};

const SeatMapGrid = ({ data }) => {
  const [seatingData, setSeatingData] = useState(data);
  const [activeStudent, setActiveStudent] = useState(null);
  const [notifications, setNotifications] = useState([]);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));

  const roomsWithGrids = useMemo(() => {
    return seatingData.rooms.map((room, roomIdx) => {
      const maxRow = Math.max(...room.seats.map(s => s.row), 0, 5); // Minimum 5 rows for aesthetics
      const maxCol = Math.max(...room.seats.map(s => s.col), 0, 5); // Minimum 5 columns
      
      const grid = Array.from({ length: maxRow }, (_, r) => 
        Array.from({ length: maxCol }, (_, c) => {
          const seat = room.seats.find(s => s.row === r + 1 && s.col === c + 1);
          return seat || null;
        })
      );

      const depts = [...new Set(room.seats.filter(s => s.student_name).map(s => s.dept))];
      return { ...room, grid, maxRow, maxCol, depts, roomIdx };
    });
  }, [seatingData]);

  const addNotification = (msg, type = 'info') => {
    const id = Date.now();
    setNotifications(prev => [{ id, msg, type }, ...prev]);
    setTimeout(() => setNotifications(prev => prev.filter(n => n.id !== id)), 5000);
  };

  const handleDragStart = (event) => {
    setActiveStudent(event.active.data.current);
  };

  const handleDragEnd = async (event) => {
    setActiveStudent(null);
    const { active, over } = event;
    if (!over) return;

    const source = active.data.current;
    const target = over.data.current;
    const targetRoom = seatingData.rooms[target.roomIdx];
    const occupant = targetRoom.seats.find(s => s.row === target.row && s.col === target.col);

    // Identify Operation: Move or Swap
    const isSwap = !!occupant;

    // Optimistic Update
    const newRooms = [...seatingData.rooms];
    
    if (isSwap) {
      addNotification(`Swapping ${source.student_name} with ${occupant.student_name}`, 'warning');
      // Swap coordinates logic
      const sourceRoomIdx = source.roomIdx ?? 0; // In case roomIdx is missing from source data
      const sourceRoom = newRooms[sourceRoomIdx];
      
      const s1 = sourceRoom.seats.find(s => s.reg_no === source.reg_no);
      const s2 = targetRoom.seats.find(s => s.reg_no === occupant.reg_no);
      
      if (s1 && s2) {
        const temp = { row: s1.row, col: s1.col };
        s1.row = s2.row; s1.col = s2.col;
        s2.row = temp.row; s2.col = temp.col;
      }
    } else {
      addNotification(`Moving ${source.student_name} to R${target.row}C${target.col}`);
      const sourceRoomIdx = source.roomIdx ?? 0;
      const sourceRoom = newRooms[sourceRoomIdx];
      const studentIdx = sourceRoom.seats.findIndex(s => s.reg_no === source.reg_no);
      if (studentIdx !== -1) {
        // Correct way: remove from source, add to target (in case rooms are different)
        const [movedStudent] = sourceRoom.seats.splice(studentIdx, 1);
        movedStudent.row = target.row;
        movedStudent.col = target.col;
        targetRoom.seats.push(movedStudent);
      }
    }

    setSeatingData({ ...seatingData, rooms: newRooms });

    // Mock API call simulation
    try {
      console.log(`API Call: PATCH /seating/plans/1/${isSwap ? 'swap' : 'move'}`, { 
        source: source.reg_no, 
        target: isSwap ? occupant.reg_no : { row: target.row, col: target.col } 
      });
      // Verification of constraint (mocking a warning)
      const isNeighborSameDept = targetRoom.seats.some(s => 
        s.reg_no !== source.reg_no && 
        s.dept === source.dept && 
        Math.abs(s.row - target.row) <= 1 && 
        Math.abs(s.col - target.col) <= 1
      );
      if (isNeighborSameDept) {
        addNotification("Constraint Warning: Adjacent student from same department!", 'error');
      }
    } catch (e) {
      addNotification("Sync failed. Local state may be inconsistent.", 'error');
    }
  };

  return (
    <DndContext 
      sensors={sensors} 
      onDragStart={handleDragStart} 
      onDragEnd={handleDragEnd}
    >
      <div className="p-8 bg-slate-950 min-h-screen text-slate-100 font-sans relative">
        {/* Toast System */}
        <div className="fixed top-8 right-8 z-[1000] flex flex-col gap-3 max-w-sm w-full pointer-events-none">
          {notifications.map(n => (
            <div 
              key={n.id} 
              className={`p-4 rounded-xl border flex items-center gap-3 animate-in fade-in slide-in-from-right shadow-2xl pointer-events-auto
                ${n.type === 'error' ? 'bg-red-500/20 border-red-500/50 text-red-100' : 
                  n.type === 'warning' ? 'bg-amber-500/20 border-amber-500/50 text-amber-100' : 
                  'bg-blue-500/20 border-blue-500/50 text-blue-100'}`}
            >
              {n.type === 'error' ? <AlertTriangle className="shrink-0 w-5 h-5"/> : <Info className="shrink-0 w-5 h-5"/>}
              <p className="text-sm font-semibold">{n.msg}</p>
            </div>
          ))}
        </div>

        <header className="mb-12 border-b border-slate-800 pb-6 flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400 bg-clip-text text-transparent">
              Visual Seat Map Editor
            </h1>
            <p className="text-slate-400 mt-2">Drag students to manual override or swap assignments.</p>
          </div>
          <div className="flex gap-4">
             <button className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-2.5 rounded-xl font-bold text-sm shadow-xl shadow-blue-500/20 transition-all active:scale-95">
               Save Changes
             </button>
             <button className="bg-slate-800 hover:bg-slate-700 text-slate-300 px-6 py-2.5 rounded-xl font-bold text-sm border border-slate-700">
               Discard
             </button>
          </div>
        </header>

        <div className="space-y-16">
          {roomsWithGrids.map((room) => (
            <section key={room.roomIdx} className="bg-slate-900/50 rounded-[2rem] p-10 border border-slate-800 shadow-3xl">
              <div className="flex items-center justify-between mb-10">
                <div className="flex items-center gap-4">
                  <div className="p-4 bg-indigo-500/10 rounded-2xl border border-indigo-500/20">
                    <Layers className="text-indigo-400 w-7 h-7" />
                  </div>
                  <div>
                    <h2 className="text-3xl font-bold text-white tracking-tight">{room.room_name}</h2>
                    <div className="flex gap-3 items-center mt-1">
                       <span className="text-slate-400 text-sm font-medium">{room.seats.length} Assignments</span>
                       <span className="w-1 h-1 bg-slate-700 rounded-full" />
                       <span className="text-slate-500 text-sm">{room.maxRow}×{room.maxCol} Matrix</span>
                    </div>
                  </div>
                </div>

                <div className="flex flex-wrap gap-3 items-center bg-black/40 p-5 rounded-2xl border border-slate-800">
                  {room.depts.map(dept => (
                    <div key={dept} className="flex items-center gap-2.5 bg-slate-800/80 px-4 py-2 rounded-xl border border-slate-700 hover:border-slate-500 transition-colors cursor-default">
                      <div className={`w-3.5 h-3.5 rounded-full shadow-inner ${DEPT_COLORS[dept.toUpperCase()] || DEFAULT_COLOR}`} />
                      <span className="text-xs font-bold uppercase tracking-wide text-slate-200">{dept}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="overflow-x-auto pb-6 scrollbar-hide">
                <div 
                  className="grid gap-5 mx-auto w-fit"
                  style={{ 
                    gridTemplateColumns: `repeat(${room.maxCol}, minmax(160px, 1fr))` 
                  }}
                >
                  {room.grid.map((row, rIdx) => (
                    <React.Fragment key={rIdx}>
                      {row.map((seat, cIdx) => (
                        <DroppableSeat 
                          key={`${rIdx}-${cIdx}`} 
                          row={rIdx + 1} 
                          col={cIdx + 1} 
                          roomIdx={room.roomIdx}
                          isOccupied={!!seat}
                        >
                          {seat && <DraggableStudent student={{...seat, roomIdx: room.roomIdx}} />}
                        </DroppableSeat>
                      ))}
                    </React.Fragment>
                  ))}
                </div>
              </div>
            </section>
          ))}
        </div>

        <DragOverlay dropAnimation={{
          sideEffects: defaultDropAnimationSideEffects({
            styles: {
              active: {
                opacity: '0.5',
              },
            },
          }),
        }}>
          {activeStudent ? <DraggableStudent student={activeStudent} isOverlay /> : null}
        </DragOverlay>
      </div>
    </DndContext>
  );
};

export default SeatMapGrid;
