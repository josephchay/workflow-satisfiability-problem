class Solution:
    def __init__(self, assignment, time):
        self.assignment = assignment
        self.time = time

    def save(self, filename):
        with open(filename, 'w') as f:
            if not self.assignment:
                f.write('unsat\n')
            else:
                f.write('sat\n')

            f.write(f'{self.time}\n')
            if self.assignment:
                for s in range(len(self.assignment)):
                    f.write(f'Step {s+1} -> User {self.assignment[s]+1}\n')

    def test_satisfiability(self, instance):
        # Check authorizations
        for s in range(instance.k):
            if not instance.auths[self.assignment[s]].collection[s]:
                return False

        # Check all constraints
        for c in instance.cons:
            if not c.test_satisfiability(self):
                return False

        return True
