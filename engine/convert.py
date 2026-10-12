from typing import Set, Dict, Tuple, FrozenSet, Any, List
from .dfa import DFA

EPS_SET = {None, "", "eps", "EPS", "ε"}

def extract_edges(transitions):
    """
    Convert NFA transitions into a list of edges: (src, sym, dst)
    Works with common dict layouts.
    """
    edges = []

    # list of (src, sym, dst)
    if isinstance(transitions, (list, tuple)):
        for item in transitions:
            if isinstance(item, (list, tuple)) and len(item) == 3:
                edges.append((item[0], item[1], item[2]))
        return edges

    if isinstance(transitions, dict):
        for k, v in transitions.items():
            # {(src, sym): {dsts}}
            if isinstance(k, tuple) and len(k) == 2:
                src, sym = k
                dsts = v
                if isinstance(dsts, (set, list, tuple)):
                    for d in dsts:
                        edges.append((src, sym, d))
                else:
                    edges.append((src, sym, dsts))

            # {src: {sym: {dsts}}}
            elif isinstance(v, dict):
                src = k
                for sym, dsts in v.items():
                    if isinstance(dsts, (set, list, tuple)):
                        for d in dsts:
                            edges.append((src, sym, d))
                    else:
                        edges.append((src, sym, dsts))

    return edges

def build_adj(edges):
    """
    adjacency: adj[src][sym] = set(dsts)
    """
    adj = {}
    alphabet = set()

    for s, sym, d in edges:
        adj.setdefault(s, {}).setdefault(sym, set()).add(d)
        if sym not in EPS_SET:
            alphabet.add(str(sym))
    return adj, alphabet

def epsilon_closure(states: Set[Any], adj: Dict[Any, Dict[Any, Set[Any]]]) -> Set[Any]:
    """
    All states reachable via ε transitions (including starting states).
    """
    stack = list(states)
    closure = set(states)

    while stack:
        s = stack.pop()
        for sym, dsts in adj.get(s, {}).items():
            if sym in EPS_SET:
                for d in dsts:
                    if d not in closure:
                        closure.add(d)
                        stack.append(d)
    return closure

def move(states: Set[Any], symbol: str, adj: Dict[Any, Dict[Any, Set[Any]]]) -> Set[Any]:
    """
    From a set of NFA states, move with 'symbol' on one step.
    """
    out = set()
    for s in states:
        for sym, dsts in adj.get(s, {}).items():
            if sym not in EPS_SET and str(sym) == symbol:
                out |= set(dsts)
    return out

def nfa_to_dfa(nfa) -> DFA:
    """
    Subset Construction:
    DFA state = set of NFA states (we store as frozenset)
    """
    edges = extract_edges(nfa.transitions)
    adj, alphabet = build_adj(edges)

    start_set = epsilon_closure({nfa.start}, adj)
    start = frozenset(start_set)

    unmarked = [start]
    dfa_states = {start}
    dfa_accept = set()
    dfa_trans = {}

    nfa_accept = set(nfa.accept)

    while unmarked:
        T = unmarked.pop()

        # if ANY NFA accept in this subset => DFA accept
        if any(s in nfa_accept for s in T):
            dfa_accept.add(T)

        for a in sorted(alphabet):
            U = epsilon_closure(move(set(T), a, adj), adj)
            U_fs = frozenset(U)

            if len(U_fs) == 0:
                continue  # skip dead/empty transitions for now

            dfa_trans[(T, a)] = U_fs

            if U_fs not in dfa_states:
                dfa_states.add(U_fs)
                unmarked.append(U_fs)

    return DFA(
        start=start,
        accept=set(dfa_accept),
        alphabet=set(alphabet),
        transitions=dfa_trans
    )
