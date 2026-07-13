import streamlit as st
import pandas as pd
import random
import io
import re

st.set_page_config(page_title="Smart Exam Seating", page_icon="🪑", layout="wide")
st.title("🪑 Smart Exam Seating Arrangement System")
st.markdown("**Fair • Secure • Instant • Anti-Cheating**  \n*Fully compatible with Soundarya Institute Student List 2026*")

# --------------------- Sidebar ---------------------
with st.sidebar:
    st.header("📋 How to Use")
    st.markdown("""
    1. Export PDF → Excel (or CSV)  
    2. Upload the file (title rows are now auto-skipped)  
    3. Add classrooms  
    4. Click **Generate Seating**  
    5. Download report
    """)
    st.success("✅ Smart header detection added – works even if your Excel has extra title rows above the table.")

# --------------------- Smart File Loader (NEW) ---------------------
def load_student_data(uploaded_file):
    if uploaded_file.name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    
    # Try different header rows (common in PDF exports)
    for header_row in range(0, 10):
        try:
            df = pd.read_excel(uploaded_file, header=header_row, engine="openpyxl")
            # Clean column names
            df.columns = df.columns.astype(str).str.strip()
            
            # Flexible column matching
            col_map = {}
            for col in df.columns:
                c = col.lower().replace(" ", "").replace(".", "")
                if "sino" in c or "slno" in c or "si.no" in c:
                    col_map[col] = "Si. No."
                elif "class" in c:
                    col_map[col] = "Class"
                elif "firstname" in c or "first name" in c or "first" in c:
                    col_map[col] = "FirstName"
                elif "regno" in c or "reg.no" in c or "reg" in c and "no" in c:
                    col_map[col] = "Reg. No."
            
            if len(col_map) >= 4:  # Found all required columns
                df = df.rename(columns=col_map)
                # Keep only the columns we need
                df = df[["Si. No.", "Class", "FirstName", "Reg. No."]].copy()
                # Drop any completely empty rows at the top
                df = df.dropna(how='all').reset_index(drop=True)
                return df
        except:
            continue
    
    # Fallback
    return pd.read_excel(uploaded_file, engine="openpyxl")

# --------------------- File Upload ---------------------
uploaded_file = st.file_uploader("📤 Upload Student Data (Excel or CSV)", type=["xlsx", "csv"])

if uploaded_file:
    students_df = load_student_data(uploaded_file)
    
    st.success(f"✅ Loaded {len(students_df)} students – headers detected automatically!")
    st.dataframe(students_df.head(10), use_container_width=True)

    # Required columns check (now after smart loading)
    required_cols = ["Si. No.", "Class", "FirstName", "Reg. No."]
    if not all(col in students_df.columns for col in required_cols):
        st.error("❌ Still couldn't detect columns. Please send me a screenshot of the first 5 rows of your Excel and I'll fix it instantly.")
        st.stop()

    # --------------------- Prepare Internal Data ---------------------
    internal_df = students_df.rename(columns={
        "Reg. No.": "Student_ID",
        "FirstName": "Name",
        "Class": "Department"
    }).copy()

    # Extract Semester for display
    internal_df['Semester'] = internal_df['Department'].str.extract(r'(\w+ Sem)', expand=False).fillna("Unknown")

    # --------------------- Define Classrooms ---------------------
    st.subheader("🏫 Define Classrooms")
    
    if "rooms" not in st.session_state:
        st.session_state.rooms = []

    col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
    with col1:
        room_name = st.text_input("Room Name (e.g., Hall101)")
    with col2:
        rows = st.number_input("Rows", min_value=1, max_value=30, value=5)
    with col3:
        cols = st.number_input("Columns", min_value=1, max_value=30, value=6)
    with col4:
        if st.button("➕ Add Room", type="primary"):
            st.session_state.rooms.append({
                "name": room_name or f"Room{len(st.session_state.rooms)+1}",
                "rows": int(rows),
                "cols": int(cols)
            })
            st.rerun()

    if st.session_state.rooms:
        room_df = pd.DataFrame(st.session_state.rooms)
        st.dataframe(room_df, use_container_width=True)
        
        if st.button("🗑️ Clear All Rooms"):
            st.session_state.rooms = []
            st.rerun()

    # --------------------- Generate Button ---------------------
    if st.session_state.rooms and len(internal_df) > 0:
        if st.button("🚀 Generate Optimized Seating Plans", type="primary", use_container_width=True):
            with st.spinner("Optimizing seats (minimizing same-Class clusters)..."):
                def allocate_seats_to_room(room_students, rows, cols):
                    num_stu = len(room_students)
                    capacity = rows * cols
                    if num_stu > capacity:
                        return None, None
                    room_students = room_students.copy().reset_index(drop=True)
                    best_plan = None
                    best_conflicts = float('inf')
                    for _ in range(50):
                        shuffled = room_students.sample(frac=1).reset_index(drop=True)
                        positions = [(r, c) for r in range(1, rows+1) for c in range(1, cols+1)][:num_stu]
                        plan = shuffled.copy()
                        plan['Row'] = [p[0] for p in positions]
                        plan['Col'] = [p[1] for p in positions]
                        conflicts = 0
                        # Horizontal conflicts
                        for r in range(1, rows+1):
                            row_df = plan[plan['Row'] == r].sort_values('Col')
                            for i in range(1, len(row_df)):
                                if row_df.iloc[i]['Department'] == row_df.iloc[i-1]['Department']:
                                    conflicts += 1
                        # Vertical conflicts
                        for c in range(1, cols+1):
                            col_df = plan[plan['Col'] == c].sort_values('Row')
                            for i in range(1, len(col_df)):
                                if col_df.iloc[i]['Department'] == col_df.iloc[i-1]['Department']:
                                    conflicts += 1
                        if conflicts < best_conflicts:
                            best_conflicts = conflicts
                            best_plan = plan.copy()
                    return best_plan, best_conflicts

                students_shuffled = internal_df.sample(frac=1).reset_index(drop=True)
                current_idx = 0
                seating_plans = {}
                total_conflicts = 0
                
                for room in st.session_state.rooms:
                    cap = room['rows'] * room['cols']
                    room_stu = students_shuffled.iloc[current_idx: current_idx + cap]
                    current_idx += cap
                    plan, conflicts = allocate_seats_to_room(room_stu, room['rows'], room['cols'])
                    if plan is not None:
                        seating_plans[room['name']] = (plan, conflicts)
                        total_conflicts += conflicts

                st.success(f"✅ Seating plans generated! Total same-Class conflicts minimized to **{total_conflicts}**")

                # Display & Download (with your original column names)
                tabs = st.tabs(list(seating_plans.keys()))
                for idx, room_name in enumerate(seating_plans.keys()):
                    with tabs[idx]:
                        plan, conf = seating_plans[room_name]
                        display_df = plan[['Row', 'Col', 'Student_ID', 'Name', 'Department', 'Semester']].copy()
                        display_df = display_df.rename(columns={
                            "Student_ID": "Reg. No.",
                            "Name": "FirstName",
                            "Department": "Class"
                        }).sort_values(['Row', 'Col'])
                        st.dataframe(display_df, use_container_width=True, hide_index=True)
                        st.caption(f"Conflicts in {room_name}: **{conf}**")

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    for room_name, (plan, _) in seating_plans.items():
                        display_df = plan[['Row', 'Col', 'Student_ID', 'Name', 'Department', 'Semester']].copy()
                        display_df = display_df.rename(columns={
                            "Student_ID": "Reg. No.",
                            "Name": "FirstName",
                            "Department": "Class"
                        }).sort_values(['Row', 'Col'])
                        display_df.to_excel(writer, sheet_name=room_name, index=False)
                output.seek(0)
                
                st.download_button(
                    label="📥 Download Complete Seating Report (Excel)",
                    data=output,
                    file_name="Exam_Seating_Arrangement_2026.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )