import re

from components import Instance


class FileReader:
    """Handles reading and parsing problem files"""

    @staticmethod
    def read_file(filename):
        def read_attribute(name):
            line = f.readline()
            match = re.match(f'{name}:\\s*(\\d+)$', line)
            if match:
                return int(match.group(1))
            else:
                raise Exception("Could not parse line {line}; expected the {name} attribute")

        instance = Instance()

        with open(filename) as f:
            instance.number_of_steps = read_attribute("#Steps")
            instance.number_of_users = read_attribute("#Users")
            instance.number_of_constraints = read_attribute("#Constraints")
            instance.auth = [[] for u in range(instance.number_of_users)]

            for i in range(instance.number_of_constraints):
                l = f.readline()
                m = re.match(r"Authorisations u(\d+)(?: s\d+)*", l)
                if m:
                    user_id = int(m.group(1))
                    steps = [-1]
                    for m in re.finditer(r's(\d+)', l):
                        if -1 in steps:
                            steps.remove(-1)
                        steps.append(int(m.group(1)) - 1)
                    instance.auth[user_id - 1].extend(steps)
                    continue

                m = re.match(r'Separation-of-duty s(\d+) s(\d+)', l)
                if m:
                    steps = (int(m.group(1)) - 1, int(m.group(2)) - 1)
                    instance.SOD.append(steps)
                    continue

                m = re.match(r'Binding-of-duty s(\d+) s(\d+)', l)
                if m:
                    steps = (int(m.group(1)) - 1, int(m.group(2)) - 1)
                    instance.BOD.append(steps)
                    continue

                m = re.match(r'At-most-k (\d+) (s\d+)(?: (s\d+))*', l)
                if m:
                    k = int(m.group(1))
                    steps = []
                    for m in re.finditer(r's(\d+)', l):
                        steps.append(int(m.group(1)) - 1)
                    instance.at_most_k.append((k, steps))
                    continue

                m = re.match(r'One-team\s+(s\d+)(?: s\d+)* (\((u\d+)\))', l)
                if m:
                    steps = []
                    for m in re.finditer(r's(\d+)', l):
                        steps.append(int(m.group(1)) - 1)
                    teams = []
                    for m in re.finditer(r'\((u\d+\s*)+\)', l):
                        team = []
                        for users in re.finditer(r'u(\d+)', m.group(0)):
                            team.append(int(users.group(1)) - 1)
                        teams.append(team)
                    instance.one_team.append((steps, teams))
                    continue
                else:
                    raise Exception(f'Failed to parse this line: {l}')
        return instance
