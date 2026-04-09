import sys

path = r'd:\My Things\PROJECTS\seating arrengement\templates\dashboard\rooms.html'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix student_name (226-227)
if '{{' in lines[225] and 'seat.student_name }}' in lines[226]:
    lines[225] = '                                                    <p class="text-md font-black italic truncate leading-tight">{{ seat.student_name }}</p>\n'
    lines[226] = ''

# Fix student_usn (228-230)
if '{{' in lines[229] and 'seat.student_usn }}' in lines[229]: # Check indices again
    pass # Wait, let's just do it based on content.

new_lines = []
skip = False
for i, line in enumerate(lines):
    if skip:
        skip = False
        continue
    
    # 1. Row Num
    if 'Row {{' in line and 'row.num }}' in lines[i+1]:
        new_lines.append(line.replace('Row {{', f'Row {{{{ row.num }}}}').replace('\n', '') + '</span>\n')
        skip = True
        continue
        
    # 2. student_name
    if 'leading-tight">{{' in line and 'seat.student_name }}' in lines[i+1]:
        new_lines.append(line.replace('{{', f'{{{{ seat.student_name }}}}').replace('\n', '') + '</p>\n')
        skip = True
        continue

    # 3. student_usn
    if 'lowercase">' in line and '{{ seat.student_usn }}' in lines[i+1]:
        new_lines.append(line.replace('lowercase">', 'lowercase">{{ seat.student_usn }}').replace('\n', '') + '</p>\n')
        skip = True
        continue
        
    # 4. dept
    if 'tracking-tighter' in line and '{{ seat.dept }}' in lines[i+1]:
        new_lines.append(line.replace('tracking-tighter', 'tracking-tighter">{{ seat.dept }}').replace('\n', '') + '</p>\n')
        skip = True
        continue

    new_lines.append(line)

# Correctly filter out empty or duplicate remnants
with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
