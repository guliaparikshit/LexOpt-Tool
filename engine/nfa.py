# nfa.py
# Module B: Regex to NFA using Thompson's Construction

EPSILON = 'ε'


class NFA:
    def __init__(self, start, accept, transitions):
        self.start = start
        self.accept = accept
        self.transitions = transitions


state_id = 0


def new_state():
    global state_id
    s = state_id
    state_id += 1
    return s


def symbol_nfa(symbol):
    start = new_state()
    end = new_state()
    transitions = {
        start: {symbol: {end}}
    }
    return NFA(start, {end}, transitions)


# -----------------------------
# Thompson operators
# -----------------------------

def merge_transitions(t1, t2):
    """Merge two transition dicts safely."""
    out = {}
    for t in (t1, t2):
        for s, mp in t.items():
            out.setdefault(s, {})
            for sym, dsts in mp.items():
                out[s].setdefault(sym, set())
                out[s][sym] |= set(dsts)
    return out


def add_epsilon(transitions, src, dst):
    transitions.setdefault(src, {})
    transitions[src].setdefault(EPSILON, set())
    transitions[src][EPSILON].add(dst)


def concat_nfa(nfa1, nfa2):
    """Concatenation: connect accept(s) of nfa1 to start of nfa2 using ε."""
    transitions = merge_transitions(nfa1.transitions, nfa2.transitions)
    for a in nfa1.accept:
        add_epsilon(transitions, a, nfa2.start)
    return NFA(nfa1.start, set(nfa2.accept), transitions)


def union_nfa(nfa1, nfa2):
    """OR (|): new start -> nfa1/nfa2 start by ε, and their accept -> new end by ε."""
    start = new_state()
    end = new_state()

    transitions = merge_transitions(nfa1.transitions, nfa2.transitions)
    add_epsilon(transitions, start, nfa1.start)
    add_epsilon(transitions, start, nfa2.start)

    for a in nfa1.accept:
        add_epsilon(transitions, a, end)
    for a in nfa2.accept:
        add_epsilon(transitions, a, end)

    return NFA(start, {end}, transitions)


def star_nfa(nfa):
    """Kleene star (*): 0 or more."""
    start = new_state()
    end = new_state()
    transitions = merge_transitions(nfa.transitions, {})

    # start -> end (empty)
    add_epsilon(transitions, start, end)
    # start -> nfa.start
    add_epsilon(transitions, start, nfa.start)

    # nfa.accept -> end and nfa.accept -> nfa.start (loop)
    for a in nfa.accept:
        add_epsilon(transitions, a, end)
        add_epsilon(transitions, a, nfa.start)

    return NFA(start, {end}, transitions)


def plus_nfa(nfa):
    """Plus (+): 1 or more. Equivalent to: nfa concatenated with nfa*"""
    return concat_nfa(nfa, star_nfa(copy_nfa(nfa)))


def optional_nfa(nfa):
    """Optional (?): 0 or 1. Equivalent to: (ε | nfa)"""
    eps_start = new_state()
    eps_end = new_state()
    eps_trans = {}
    add_epsilon(eps_trans, eps_start, eps_end)
    eps_nfa = NFA(eps_start, {eps_end}, eps_trans)
    return union_nfa(eps_nfa, nfa)


def copy_nfa(nfa):
    """A light copy to avoid reusing same objects/states in plus."""
    # NOTE: states are just ints; transitions map to sets
    trans = {}
    for s, mp in nfa.transitions.items():
        trans[s] = {}
        for sym, dsts in mp.items():
            trans[s][sym] = set(dsts)
    return NFA(nfa.start, set(nfa.accept), trans)


# -----------------------------
# Regex parsing: to postfix
# -----------------------------

def is_literal(ch):
    """Literal characters (basic). We'll treat letters/digits/_ as literals."""
    return ch.isalnum() or ch == '_'


def tokenize(regex):
    """
    Tokenize regex.
    Supports: literals, (), |, *, +, ?, and character classes like [a-zA-Z_]
    For character classes: we'll expand them to a special token like ('CLASS', set_of_chars).
    """
    tokens = []
    i = 0
    while i < len(regex):
        c = regex[i]

        if c.isspace():
            i += 1
            continue

        if c in {'(', ')', '|', '*', '+', '?'}:
            tokens.append(c)
            i += 1
            continue

        if c == '[':
            j = i + 1
            chars = set()
            while j < len(regex) and regex[j] != ']':
                if j + 2 < len(regex) and regex[j+1] == '-' and regex[j+2] != ']':
                    # range a-z
                    start = regex[j]
                    end = regex[j+2]
                    for code in range(ord(start), ord(end) + 1):
                        chars.add(chr(code))
                    j += 3
                else:
                    chars.add(regex[j])
                    j += 1
            if j >= len(regex) or regex[j] != ']':
                raise ValueError("Unclosed character class: missing ']'")
            tokens.append(('CLASS', chars))
            i = j + 1
            continue

        # literal single char
        tokens.append(c)
        i += 1

    return tokens


def insert_concat(tokens):
    """
    Insert explicit concatenation operator '.' where needed.
    Rules:
      If token A can end an expression AND token B can start an expression -> insert '.'
    """
    def can_end(tok):
        return (
            tok == ')' or tok in {'*', '+', '?'} or isinstance(tok, tuple) or (isinstance(tok, str) and tok not in {'(', '|'})
        )

    def can_start(tok):
        return tok == '(' or isinstance(tok, tuple) or (isinstance(tok, str) and tok not in {')', '|', '*', '+', '?'})

    out = []
    for k in range(len(tokens)):
        out.append(tokens[k])
        if k < len(tokens) - 1:
            a = tokens[k]
            b = tokens[k+1]
            if can_end(a) and can_start(b):
                out.append('.')  # explicit concat
    return out


def to_postfix(tokens):
    """
    Shunting-yard to convert tokens to postfix (RPN).
    Precedence:  *, +, ? highest (unary postfix)
                 . next
                 | lowest
    """
    prec = {'|': 1, '.': 2, '*': 3, '+': 3, '?': 3}
    output = []
    stack = []

    for tok in tokens:
        if tok == '(':
            stack.append(tok)
        elif tok == ')':
            while stack and stack[-1] != '(':
                output.append(stack.pop())
            if not stack:
                raise ValueError("Mismatched parentheses")
            stack.pop()  # remove '('
        elif tok in prec:
            # unary postfix operators (* + ?) go directly by precedence rules
            while stack and stack[-1] != '(' and prec.get(stack[-1], 0) >= prec[tok]:
                output.append(stack.pop())
            stack.append(tok)
        else:
            # literal or class
            output.append(tok)

    while stack:
        if stack[-1] == '(':
            raise ValueError("Mismatched parentheses")
        output.append(stack.pop())

    return output


# -----------------------------
# Postfix -> NFA
# -----------------------------

def class_nfa(char_set):
    """
    Build NFA for a character class like [a-z].
    We'll model it as multiple transitions from start to end for each char.
    """
    start = new_state()
    end = new_state()
    transitions = {start: {}}
    for ch in char_set:
        transitions[start].setdefault(ch, set()).add(end)
    return NFA(start, {end}, transitions)


def postfix_to_nfa(postfix):
    stack = []

    for tok in postfix:
        if tok == '.':
            b = stack.pop()
            a = stack.pop()
            stack.append(concat_nfa(a, b))
        elif tok == '|':
            b = stack.pop()
            a = stack.pop()
            stack.append(union_nfa(a, b))
        elif tok == '*':
            a = stack.pop()
            stack.append(star_nfa(a))
        elif tok == '+':
            a = stack.pop()
            stack.append(plus_nfa(a))
        elif tok == '?':
            a = stack.pop()
            stack.append(optional_nfa(a))
        else:
            # literal or CLASS
            if isinstance(tok, tuple) and tok[0] == 'CLASS':
                stack.append(class_nfa(tok[1]))
            else:
                stack.append(symbol_nfa(tok))

    if len(stack) != 1:
        raise ValueError("Invalid regex (stack did not end with a single NFA)")
    return stack[0]


def regex_to_nfa(regex):
    """
    Main function for Module B:
    regex string -> NFA object
    """
    global state_id
    state_id = 0  # reset per run (important!)

    tokens = tokenize(regex)
    tokens = insert_concat(tokens)
    postfix = to_postfix(tokens)
    return postfix_to_nfa(postfix)
