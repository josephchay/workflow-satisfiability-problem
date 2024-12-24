from collections import defaultdict


class Instance:
    """Represents a WSP problem instance"""
    def __init__(self):
        self.number_of_steps = 0
        self.number_of_users = 0
        self.number_of_constraints = 0
        self.auth = []
        self.SOD = []
        self.BOD = []
        self.at_most_k = []
        self.one_team = []
        self.sual = []  # List of (scope, h, super_users) tuples
        self.wang_li = []  # List of (scope, departments) tuples 
        self.ada = []  # List of (s1, s2, source_users, target_users) tuples
        self.user_step_matrix = None
        self.step_domains = {}
        self.constraint_graph = defaultdict(set)

    def compute_step_domains(self):
        """Compute possible users for each step based on authorizations"""
        for step in range(self.number_of_steps):
            self.step_domains[step] = set()
            for user in range(self.number_of_users):
                if self.user_step_matrix[user][step]:
                    self.step_domains[step].add(user)
