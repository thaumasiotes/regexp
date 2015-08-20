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
    def __init__(self, name, accept=False):
        self.name = name
        self.transitions = dict()
        self.accept = accept

    def move(self, inpt):
        dests = set()
        if inpt in self.transitions:
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
        sub_i2, sub_f2 = compile_to_nfa(tree[2], accept_final=True)
        assert sub_f1.transitions == {}
        sub_f1.transitions = sub_i2.transitions
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
    old_states = states.copy()
    new_states = states.copy()
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
