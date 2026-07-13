import random
import math
import copy

class SeatingScorer:
    """
    Evaluates the quality of a seating arrangement based on academic integrity.
    """
    WEIGHTS = {
        'h_dept': -15,   # Horizontal/Vertical same Department
        'h_sem': -10,    # Horizontal/Vertical same Semester
        'h_subject': -20, # Horizontal/Vertical same Subject
        'd_dept': -5,    # Diagonal same Department
        'd_sem': -3,     # Diagonal same Semester
    }

    @classmethod
    def calculate_assignment_score(cls, assignments):
        """
        Calculate total academic integrity score for a set of assignments.
        Higher is better.
        Assignments is a list of dictionaries as returned by the CSP engine.
        """
        if not assignments:
            return 0

        score = 0
        # Build map for fast neighbor lookup
        seat_map = {(a['row'], a['col']): a for a in assignments}
        
        for a in assignments:
            row, col = a['row'], a['col']
            
            # Check neighbors
            h_neighbors = [(row, col-1), (row, col+1), (row-1, col), (row+1, col)]
            d_neighbors = [(row-1, col-1), (row-1, col+1), (row+1, col-1), (row+1, col+1)]
            
            for nr, nc in h_neighbors:
                if (nr, nc) in seat_map:
                    n = seat_map[(nr, nc)]
                    if n['program_id'] == a['program_id']:
                        score += cls.WEIGHTS['h_dept']
                    if n['semester'] == a['semester']:
                        score += cls.WEIGHTS['h_sem']
                    if n['subject'] == a['subject']:
                        score += cls.WEIGHTS['h_subject']
            
            for nr, nc in d_neighbors:
                if (nr, nc) in seat_map:
                    n = seat_map[(nr, nc)]
                    if n['program_id'] == a['program_id']:
                        score += cls.WEIGHTS['d_dept']
                    if n['semester'] == a['semester']:
                        score += cls.WEIGHTS['d_sem']
        
        # Divide by 2 because each pair is counted twice
        return score / 2

class SeatingOptimizer:
    """
    Refines a seating arrangement using Simulated Annealing.
    """
    def __init__(self, iterations=1000, initial_temp=100, cooling_rate=0.99):
        self.iterations = iterations
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate

    def refine(self, assignments):
        """
        Attempt to improve the seating arrangement by swapping students.
        Only swaps within the same room for now.
        """
        if not assignments:
            return assignments

        # Group by room
        room_groups = {}
        for a in assignments:
            rid = a['room'].id
            if rid not in room_groups:
                room_groups[rid] = []
            room_groups[rid].append(a)

        refined_assignments = []

        for rid, room_assigns in room_groups.items():
            if len(room_assigns) < 2:
                refined_assignments.extend(room_assigns)
                continue

            current_assigns = copy.deepcopy(room_assigns)
            current_score = SeatingScorer.calculate_assignment_score(current_assigns)
            
            temp = self.initial_temp
            
            for i in range(self.iterations):
                # Pick two random indices to swap
                idx1, idx2 = random.sample(range(len(current_assigns)), 2)
                
                # Perform swap
                # We swap the student data but KEEP the room/row/col/seat_pos
                s1 = current_assigns[idx1]
                s2 = current_assigns[idx2]
                
                # Swap student-related fields
                (s1['student'], s1['exam_group'], s1['program_id'], s1['semester'], s1['subject'], s1['university_id'],
                 s2['student'], s2['exam_group'], s2['program_id'], s2['semester'], s2['subject'], s2['university_id']) = (
                 s2['student'], s2['exam_group'], s2['program_id'], s2['semester'], s2['subject'], s2['university_id'],
                 s1['student'], s1['exam_group'], s1['program_id'], s1['semester'], s1['subject'], s1['university_id']
                )
                
                new_score = SeatingScorer.calculate_assignment_score(current_assigns)
                
                # Decision
                if new_score > current_score:
                    current_score = new_score
                else:
                    # Acceptance probability
                    prob = math.exp((new_score - current_score) / temp)
                    if random.random() < prob:
                        current_score = new_score
                    else:
                        # Revert swap
                        (s1['student'], s1['exam_group'], s1['program_id'], s1['semester'], s1['subject'], s1['university_id'],
                         s2['student'], s2['exam_group'], s2['program_id'], s2['semester'], s2['subject'], s2['university_id']) = (
                         s2['student'], s2['exam_group'], s2['program_id'], s2['semester'], s2['subject'], s2['university_id'],
                         s1['student'], s1['exam_group'], s1['program_id'], s1['semester'], s1['subject'], s1['university_id']
                        )
                
                temp *= self.cooling_rate

            refined_assignments.extend(current_assigns)

        return refined_assignments

class RiskProfiler:
    """
    Calculates cheating risk metrics for a seating plan.
    """
    @staticmethod
    def calculate_risk_index(assignments, score):
        """
        Returns a risk index from 0 to 100.
        0 = Optimal, 100 = Maximum Conflict.
        """
        if not assignments:
            return 0
        
        # Absolute penalty points
        abs_score = abs(score)
        
        # Potential max penalty for normalization
        # Each student has ~4 H/V neighbors. Max penalty per student ~ (20+15+10) = 45.
        # This is a guestimate for normalization.
        max_potential_penalty = len(assignments) * 20 
        
        risk = (abs_score / max_potential_penalty) * 100 if max_potential_penalty > 0 else 0
        return min(round(risk, 1), 100.0)
