from typing import Set, Dict, Tuple, Any, FrozenSet, List
from .dfa import DFA

def minimize_dfa(dfa: DFA) -> DFA:
    """
    Hopcroft DFA minimization (classic).
    Works even if states are frozensets.
    """
    Q = dfa.states()
    Sigma = set(dfa.alphabet)
    delta = dfa.transitions
    F = set(dfa.accept)
    q0 = dfa.start

    # If no accept states, return as-is
    if not F:
        return dfa

    # Initial partition: F and non-F
    P = []
    if F:
        P.append(frozenset(F))
    NF = Q - F
    if NF:
        P.append(frozenset(NF))

    W = P.copy()  # work list

    def transition(src, sym):
        return delta.get((src, sym), None)

    while W:
        A = W.pop()

        for c in Sigma:
            # X = states that go to A on c
            X = set()
            for q in Q:
                nxt = transition(q, c)
                if nxt in A:
                    X.add(q)

            newP = []
            for Y in P:
                inter = set(Y) & X
                diff = set(Y) - X

                if inter and diff:
                    Y1 = frozenset(inter)
                    Y2 = frozenset(diff)
                    newP.extend([Y1, Y2])

                    # maintain W
                    if Y in W:
                        W.remove(Y)
                        W.extend([Y1, Y2])
                    else:
                        # add smaller part
                        if len(Y1) <= len(Y2):
                            W.append(Y1)
                        else:
                            W.append(Y2)
                else:
                    newP.append(Y)

            P = newP

    # Build mapping old_state -> block_id
    blocks = list(P)
    state_to_block = {}
    for i, block in enumerate(blocks):
        for s in block:
            state_to_block[s] = i

    new_start = state_to_block[q0]
    new_accept = set(state_to_block[s] for s in F)

    new_trans = {}
    for (src, sym), dst in delta.items():
        if dst is None:
            continue
        new_trans[(state_to_block[src], sym)] = state_to_block[dst]

    return DFA(
        start=new_start,
        accept=new_accept,
        alphabet=set(Sigma),
        transitions=new_trans
    )
