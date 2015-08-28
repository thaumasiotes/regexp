from itertools import count
import reparse

class State:
    # A State has an identifier and may be accepting or rejecting.
    # Its transitions table looks like this:
    # { 'l': [state_reachable_on_l, other_state_reachable_on_l],
    #   'q': [state_reachable_on_q],
    #   '': [state_reachable_on_empty_string] }
    # That is to say, the keys are literal values triggering the transitions,
    # and each value is a list of every state that can be reached by that
    # transition.
    CLASS_MARK = 'class transition'

    def __init__(self, name, accept=False):
        self.name = name
        self.transitions = dict()
        self.accept = accept

    def move(self, inpt):
        dests = set()
        if State.CLASS_MARK in self.transitions and self.class_pred(inpt):
            for d in self.transitions[State.CLASS_MARK]:
                dests.add(d)
        elif inpt in self.transitions:
            for d in self.transitions[inpt]:
                dests.add(d)
        return dests

    def __repr__(self):
        tlist = []
        for t in self.transitions:
            tlist.append('{}->{}'.format(repr(t), [
                s.name for s in self.transitions[t]]))
        return '(name: {}, accept: {}, transitions: {{{}}})'.format(
            self.name, self.accept, ','.join(tlist))

    def __str__(self):
        return repr(self)


def compile_to_nfa(tree, names=count(1), accept_final=True):
    '''tree is a parse tree as returned by reparse.parse;
    names and accept_final are for internal accounting and
    shouldn't be supplied.
    Returns the initial and final state of the resulting NFA'''
    c = names.next()
    initial = State('i_{}'.format(c))
    final = State('f_{}'.format(c), accept_final)
    op = tree[0]
    if op == reparse.LTRL:
        assert len(tree) == 2
        initial.transitions[tree[1]] = [final]
    elif op == reparse.DOT:
        # check ord(c) as a gimmicky way of making sure c is a character
        initial.class_pred = (lambda c: ord(c) < 256 and c != '\n')
        initial.transitions[State.CLASS_MARK] = [final]
    elif op == reparse.CLSS or op == reparse.NCLS:
        accepts = tree[1]
        ranges = [(begin, end) for _, begin, end in tree[2:]]
        def pred(c):
            if c in accepts:
                return True
            for b, e in ranges:
                if b <= c <= e:
                    return True
            return False
        initial.class_pred = pred if op == reparse.CLSS else (lambda c: not pred(c))
        initial.transitions[State.CLASS_MARK] = [final]
    elif op == reparse.STAR:
        assert len(tree) == 2
        sub_i, sub_f = compile_to_nfa(tree[1], accept_final=False)
        # a final state, by construction, never has outgoing transitions
        assert sub_f.transitions == {}
        sub_f.transitions[''] = [sub_i, final]
        initial.transitions[''] = [sub_i, final]
    elif op == reparse.CCAT:
        assert len(tree) == 3
        sub_i1, sub_f1 = compile_to_nfa(tree[1], accept_final=False)
        sub_i2, sub_f2 = compile_to_nfa(tree[2], accept_final=accept_final)
        assert sub_f1.transitions == {}
        sub_f1.transitions = sub_i2.transitions
        if State.CLASS_MARK in sub_i2.transitions:
            sub_f1.class_pred = sub_i2.class_pred
        return sub_i1, sub_f2
    elif op == reparse.DSJN:
        assert len(tree) == 3
        sub_i1, sub_f1 = compile_to_nfa(tree[1], accept_final=False)
        sub_i2, sub_f2 = compile_to_nfa(tree[2], accept_final=False)
        initial.transitions[''] = [sub_i1, sub_i2]
        assert sub_f1.transitions == {} and sub_f2.transitions == {}
        sub_f1.transitions[''] = [final]
        sub_f2.transitions[''] = [final]
    else:
        raise Exception("malformed parse tree given to regexp.compile_to_nfa")
    return initial, final


def epsilon_closure(states):
    '''given a set of states, return the set of all states that can be
    reached from anywhere in the initial set by making any number of
    transitions with the empty string'''
    old_states = set() | states
    new_states = set() | states
    visited = set()
    while True:
        for old in old_states - visited:
            if '' in old.transitions:
                for new in old.transitions['']:
                    new_states.add(new)
        if new_states <= old_states:
            break
        visited |= old_states
        old_states |= new_states
    return new_states


def move(states, c):
    '''given a set of NFA states, return the set of all states that can
    be reached by transitioning on the character c'''
    result = set()
    for state in epsilon_closure(states):
        result |= state.move(c)
    return epsilon_closure(result)


def compile_to_dfa(initial, final):
    '''Compile an NFA down to a DFA. initial is the start state of the NFA,
    and final is its accepting state. (The NFAs that we construct always
    have exactly one accepting state.) Returns the initial state of the DFA.'''
    names = count(1)
    dfa_states = set()
    dfa_state_lookup = {}
    marked = set()
    dfa_init = epsilon_closure({initial})
    dfa_init_state = State('dfa_{}'.format(names.next()))
    dfa_init_state.accept = final in dfa_init
    dfa_states.add(frozenset(dfa_init))
    dfa_state_lookup[frozenset(dfa_init)] = dfa_init_state
    while dfa_states - marked:
        # I'd like to just get an arbitrary set element here...
        processing_queue = dfa_states - marked
        for stateset in processing_queue:
            if stateset in marked:
                continue
            marked.add(frozenset(stateset))
            for byte in xrange(256):
                char = chr(byte)
                newset = move(stateset, char)
                if frozenset(newset) not in dfa_states:
                    new_dfa_state = State('dfa_{}'.format(names.next()))
                    new_dfa_state.accept = final in newset
                    dfa_states.add(frozenset(newset))
                    dfa_state_lookup[frozenset(newset)] = new_dfa_state
                dfa_state_lookup[frozenset(stateset)].transitions[char] = [
                    dfa_state_lookup[frozenset(newset)]]
    return dfa_init_state, set(dfa_state_lookup.values())


def process(init, inpt):
    '''init is the initial state of an NFA representing a regular
    expression. inpt is the input to the NFA. Returns the set of
    states reached after processing inpt, possibly the empty set.'''
    old_states = epsilon_closure({init})
    for char in inpt:
        new_states = set()
        for old in old_states:
            new_states |= old.move(char)
        old_states = epsilon_closure(new_states)
    return old_states


def dfa_process(init, inpt):
    '''Same as process, but, since init is the initial state of a DFA
    and a DFA can only be in one state at a time, try to have a little
    less overhead. Returns True if an accept state is reached, False
    otherwise.'''
    current = init
    for char in inpt:
        current = current.transitions[char][0]
    return current.accept


def minimize_dfa(init, states):
    '''Return the DFA which is equivalent to the DFA represented by init,
    but which has the minimum possible number of states. init is the start
    state of the DFA to be minimized, and states is a set containing all
    of its states. Returns the start state of the minimized DFA.'''
    partition = [set(), set()]
    def group_of(s, p):
        for idx, group in enumerate(p):
            if s in group:
                return idx
        raise Exception("bad call to group_of in minimize_dfa")
    for state in states:
        if state.accept:
            partition[0].add(state)
        else:
            partition[1].add(state)
    new_partition = partition[:]
    while True:
        for idx, group in enumerate(partition):
            byte = 0
            while byte < 256:
                char = chr(byte)
                subgroup_dict = {}
                for state in group:
                    # invoking self.move on a DFA state should return a set
                    # containing exactly one state
                    target = group_of(state.move(char).pop(), partition)
                    subgroup_dict.setdefault(target, set()).add(state)
                if len(subgroup_dict) > 1:
                    for target_group in subgroup_dict:
                        new_partition.append(subgroup_dict[target_group])
                    new_partition[idx] = None
                    byte = 0
                    break
                byte += 1
        new_partition = filter(lambda e: e is not None, new_partition)
        if new_partition == partition:
            break
        partition = new_partition[:]
    representatives = {}
    minimized_states = {}
    names = count(1)
    initial_idx = -1
    # in this pass, we choose a representative state from the original
    # DFA for each state in the minimized DFA
    for idx, group in enumerate(partition):
        representatives[idx] = group.pop()
        group.add(representatives[idx])
        if init in group:
            initial_idx = idx
    # in this pass, we create a State object for each state in the
    # minimized DFA
    for idx, group in enumerate(partition):
        new_state = State('mini_{}'.format(names.next()))
        new_state.accept = representatives[idx].accept
        minimized_states[idx] = new_state
    # in this pass, we create the transitions for the minimized DFA
    for idx, group in enumerate(partition):
        mini_state = minimized_states[idx]
        rep_state = representatives[idx]
        for char in rep_state.transitions:
            target_idx = group_of(rep_state.transitions[char][0], partition)
            target_mini = minimized_states[target_idx]
            mini_state.transitions[char] = [target_mini]
    return minimized_states[initial_idx]


def match(pattern, text):
    '''Tell whether a regular expression matches a particular string.
    pattern is the regular expression; text is the string to match.
    The pattern must match the *entire* string.'''
    re_tree = reparse.parse(pattern)
    initial, final = compile_to_nfa(re_tree)
    result_states = process(initial, text)
    # By construction, the only accepting state is the final state
    # returned by compile_to_nfa
    return final in result_states


def search(pattern, text):
    '''Find a match to the regular expression represented by pattern,
    located anywhere within text.'''
    anchor_head = '[\x00-\xff]*'
    anchor_end = '[\x00-\xff]*'
    if pattern and pattern[0] == '^':
        pattern = pattern[1:]
        anchor_head = ''
    if pattern and pattern[-1] == '$':
        pattern = pattern[:-1]
        anchor_end = ''
    pattern = '{}({}){}'.format(anchor_head, pattern, anchor_end)
    return match(pattern, text)


def match_compile(pattern):
    '''Return a compiled regular expression. It is a DFA that provides
    the method self.match(text), which will report whether pattern
    matches text in its entirety.'''
    re_tree = reparse.parse(pattern)
    nfa = compile_to_nfa(re_tree)
    dfa = compile_to_dfa(*nfa)
    mini_dfa = minimize_dfa(*dfa)
    mini_dfa.match = (lambda text: dfa_process(mini_dfa, text))
    return mini_dfa


def search_compile(pattern):
    '''Return a compiled regular expression. It is a DFA that provides
    the method self.search(text), which will detect any substring in text
    that matches pattern.'''
    anchor_head = '[\x00-\xff]*'
    anchor_end = '[\x00-\xff]*'
    if pattern and pattern[0] == '^':
        pattern = pattern[1:]
        anchor_head = ''
    if pattern and pattern[-1] == '$':
        pattern = pattern[:-1]
        anchor_end = ''
    pattern = '{}({}){}'.format(anchor_head, pattern, anchor_end)
    re_tree = reparse.parse(pattern)
    nfa = compile_to_nfa(re_tree)
    dfa = compile_to_dfa(*nfa)
    mini_dfa = minimize_dfa(*dfa)
    mini_dfa.search = (lambda text: dfa_process(mini_dfa, text))
    return mini_dfa
