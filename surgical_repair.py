import re

path = r'd:\My Things\PROJECTS\seating arrengement\templates\dashboard\rooms.html'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. FIX THE SEAT DIV (which was messed up by the global regex)
# This pattern matches the mess I made and puts back the background logic
bad_seat_mess = r'<div\s+class="w-10 h-10 rounded-xl flex items-center justify-center text-\[10px\] font-black transition-all cursor-default shadow-sm\s+.{% if seat\.occupied %}.*?{% else %}bg-emerald-500 text-white shadow-emerald-500/20 hover:scale-110 active:scale-95{% endif %}">'

correct_seat = '<div class="w-10 h-10 rounded-xl flex items-center justify-center text-[10px] font-black transition-all cursor-default shadow-sm {% if seat.occupied %}bg-rose-500 text-white shadow-rose-500/20 scale-105 active:scale-95{% else %}bg-emerald-500 text-white shadow-emerald-500/20 hover:scale-110 active:scale-95{% endif %}">'

text = re.sub(bad_seat_mess, correct_seat, text, flags=re.DOTALL)

# 2. FIX THE TOOLTIP (ensure it's clean and outside the div)
# I will use a very specific anchor: <!-- Tooltip (BookMyShow Style) -->
tooltip_block = '''                                        <!-- Tooltip (BookMyShow Style) -->
                                        {% if seat.occupied %}
                                        <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-4 hidden group-hover:block z-[300] w-64">
                                            <div class="bg-slate-900 text-white p-5 rounded-3xl shadow-2xl relative animate-in fade-in zoom-in duration-200">
                                                <div class="space-y-1">
                                                    <p class="text-[10px] font-black text-blue-400 uppercase tracking-widest italic leading-none mb-2">Assigned Student</p>
                                                    <p class="text-md font-black italic truncate leading-tight">{{ seat.student_name }}</p>
                                                    <p class="text-[11px] font-bold text-slate-400 tabular-nums lowercase">{{ seat.student_usn }}</p>
                                                    <p class="text-[10px] font-black text-slate-500 uppercase tracking-tighter mt-2 border-t border-slate-800 pt-2">{{ seat.dept }}</p>
                                                </div>
                                                <div class="absolute top-full left-1/2 -translate-x-1/2 border-8 border-transparent border-t-slate-900"></div>
                                            </div>
                                        </div>
                                        {% else %}
                                        <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-4 hidden group-hover:block z-[300] w-32">
                                            <div class="bg-slate-900 text-white py-3 px-4 rounded-2xl shadow-xl relative text-center animate-in fade-in zoom-in duration-200">
                                                <p class="text-[10px] font-black uppercase tracking-widest italic">AVAILABLE SEAT</p>
                                                <div class="absolute top-full left-1/2 -translate-x-1/2 border-8 border-transparent border-t-slate-900"></div>
                                            </div>
                                        </div>
                                        {% endif %}'''

# Replace whatever is between <!-- Tooltip --> and the next endfor/else etc.
# Actually, I'll just find the anchor and replace everything until the end of the seat's tooltip logic.
tooltip_pattern = r'<!-- Tooltip \(BookMyShow Style\) -->.*?{% endif %}'
text = re.sub(tooltip_pattern, tooltip_block, text, flags=re.DOTALL)

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
