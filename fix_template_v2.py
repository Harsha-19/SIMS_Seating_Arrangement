import sys

path = r'd:\My Things\PROJECTS\seating arrengement\templates\dashboard\rooms.html'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# Fix the broken dept tag
# Search for: class="text-[10px] font-black text-slate-500 uppercase tracking-tighter">{{ seat.dept }} mt-2 border-t border-slate-800 pt-2"></p>
# AND REPLACE WITH CORRECT VERSION
bad = '''<p
                                                        class="text-[10px] font-black text-slate-500 uppercase tracking-tighter">{{ seat.dept }} mt-2 border-t border-slate-800 pt-2"></p>'''
good = '''<p class="text-[10px] font-black text-slate-500 uppercase tracking-tighter mt-2 border-t border-slate-800 pt-2">{{ seat.dept }}</p>'''

# Also fix USN line just in case it's messy
# <p
#                                                         class="text-[11px] font-bold text-slate-400 tabular-nums lowercase">{{ seat.student_usn }}</p>
bad_usn = '''<p
                                                        class="text-[11px] font-bold text-slate-400 tabular-nums lowercase">{{ seat.student_usn }}</p>'''
good_usn = '''<p class="text-[11px] font-bold text-slate-400 tabular-nums lowercase">{{ seat.student_usn }}</p>'''

# Just use simple regex-like search since formatting is messy
import re
text = re.sub(r'<p\s+class="text-\[11px\].*?\{\{ seat.student_usn \}\}</p>', good_usn, text, flags=re.DOTALL)
text = re.sub(r'<p\s+class="text-\[10px\].*?\{\{ seat.dept \}\}.*?</p>', good, text, flags=re.DOTALL)

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
