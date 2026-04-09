import sys
import re

path = r'd:\My Things\PROJECTS\seating arrengement\templates\dashboard\rooms.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# THE COMPLETE BLOCK WE WANT
# Check if occupied...
# We define the correct piece for the assigned student tooltip

correct_tooltip = '''                                        {% if seat.occupied %}
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
                                        {% else %}'''

# Use regex to find everything from "if seat.occupied" to "else" and replace it
# The pattern must be resilient to whatever the current state is.
pattern = r'{% if seat.occupied %}.*?{% else %}'
content = re.sub(pattern, correct_tooltip, content, flags=re.DOTALL)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
