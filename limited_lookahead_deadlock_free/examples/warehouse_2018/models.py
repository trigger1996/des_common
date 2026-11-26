"""Generate the robot DFAs in Tatsumoto et al. (CEP 2018), Figs. 3--8.

The equations specify all shortest paths before and after item pickup, plus
the four task transitions. No source code from the authors is assumed.
"""

from collections import deque

from des_core.automata import DFA


TASKS = ((7, 32, 70), (4, 18, 64), (1, 38, 67))
OBSTACLES = frozenset(row * 10 + column for row in (1, 3, 5)
                      for column in (2, 3, 5, 6, 8, 9))


def grid_neighbors(q):
    row, column = divmod(q - 1, 10)

    for direction, dr, dc in ((1, -1, 0), (3, 0, 1), (5, 1, 0), (7, 0, -1)):
        r, c = row + dr, column + dc
        target = r * 10 + c + 1

        if 0 <= r < 7 and 0 <= c < 10 and target not in OBSTACLES:
            yield direction, target


def distances(q0):
    distance = {q0: 0}
    queue = deque([q0])

    while queue:
        q = queue.popleft()

        for _, target in grid_neighbors(q):
            if target not in distance:
                distance[target] = distance[q] + 1
                queue.append(target)

    return distance


def shortest_path_transitions(q0, goal, robot):
    forward = distances(q0)
    backward = distances(goal)
    length = forward[goal]
    transitions = {}

    for q, depth in forward.items():
        for direction, target in grid_neighbors(q):
            if depth + 1 + backward.get(target, length + 1) == length:
                transitions[str(q), str(10 * robot + direction)] = str(target)

    return transitions


def robot_model(robot, *, current=None):
    start, item, goal = TASKS[robot - 1]
    transitions = shortest_path_transitions(start, item - 10, robot)
    transitions.update(shortest_path_transitions(item + 10, goal, robot))
    down = str(10 * robot + 5)
    transitions.update({('0', down): str(start), (str(item - 10), down): str(item),
                        (str(item), down): str(item + 10), (str(goal), down): '71'})
    states = frozenset(q for pair, target in transitions.items() for q in (pair[0], target))
    events = frozenset(str(10 * robot + direction) for direction in (1, 3, 5, 7))
    plant = DFA(states, str(current) if current is not None else '0', events, events, events, transitions)

    return plant, frozenset({'71'})


def paper_components(current=(7, 4, 1)):
    return [robot_model(k + 1, current=q) for k, q in enumerate(current)]


def collision_free(q):
    # Waiting/delivery areas are shared spaces, not a single occupied cell.
    occupied = [cell for cell in q if cell not in ('0', '71')]

    return len(occupied) == len(set(occupied))
