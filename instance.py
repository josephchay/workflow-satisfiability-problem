# instance.py
class WSPInstance:
    def __init__(self):
        self.number_of_steps = 0
        self.number_of_users = 0
        self.number_of_constraints = 0
        self.auth = []            # List of lists: auth[user] = list of authorized steps
        self.SOD = []             # List of tuples: (step1, step2)
        self.BOD = []             # List of tuples: (step1, step2)
        self.at_most_k = []       # List of tuples: (k, [steps])
        self.one_team = []        # List of tuples: ([steps], [[team1_users], [team2_users], ...])
