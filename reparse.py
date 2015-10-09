# Regular expressions consist of literal characters (e.g. "a", or "b")
# joined by the three operations disjunction ("a|b"), concatenation ("ab")
# and Kleene star ("a*"). Intuitively, the grammar defining them looks like:
#   R -> literal
#   R -> R * (Kleene star)
#   R -> R R (concatenation)
#   R -> R | R (disjunction)
# Since this is quite ambiguous, we use a version encoding an explicit
# order of operations (first star, then concatenation, then disjunction):
#   dsjn   -> ccat dprime
#   dprime -> '|' ccat dprime
#   dprime -> '' (the empty string)
#   ccat   -> star ccat
#   ccat   -> ''
#   star   -> base '*'
#   star   -> base
#   base   -> '(' dsjn ')'
#   base   -> literal
# In assembling the parse tree, we take some shortcuts to omit any
# useless nodes that we happen to derive. For example, we prefer to
# parse the regex "a" as (LTRL, "a") rather than as
# (CCAT, (STAR, (LTRL, "a"), False), None).
# The result is a parse tree which does represent the regular expression,
# but does not perfectly represent the parsing grammar.

class Operation:
    def __init__(self,name):
        self.name = name

    def __str__(self): return self.name

    def __repr__(self): return self.name

# we'll use these in the parse tree
DSJN = Operation('DSJN')
CCAT = Operation('CCAT')
STAR = Operation('STAR')
LTRL = Operation('LTRL')
CLSS = Operation('CLSS')
NCLS = Operation('NCLS')
RNGE = Operation('RNGE')
DOT  = Operation('DOT')
GROUP = Operation('GROUP')

# Reserved characters. Forward slash is reserved in case we want to implement
# character escapes later.
RESERVED = {'.', '[', ']', '(', ')', '|', '*', '/'}

from itertools import count

def parse(inpt):
    groups = count(1)
    tree, remnant = parse_dsjn(inpt, groups)
    assert remnant == '', 'parse error: did not consume entire input - probably found a reserved character out of place'
    return tree

# base -> '(' dsjn ')'
# base -> literal
# base -> '[' elements ']'
def parse_base(inpt, groups):
    if inpt == '':
        # this means that a clause somewhere up the call stack needs to be
        # the empty string
        return None, inpt
    elif inpt[0] == '/': # escaped character
        assert len(inpt) >= 2, 'parse error: pattern terminated during character escape'
        return (LTRL, inpt[1]), inpt[2:]
    elif inpt[0] == '.': # wildcard character
        return (DOT,), inpt[1:]
    elif inpt[0] == '(': # parenthesized regexp
        group = groups.next()
        d, remnant = parse_dsjn(inpt[1:], groups)
        assert remnant and remnant[0] == ')', 'parse error: no closing ) for earlier ('
        return (GROUP, group, d), remnant[1:]
    elif inpt[0] == '[': # character class
        assert len(inpt) >= 2, 'parse error: malformed character class'
        if inpt[1] == '^': # negative character class
            elements, remnant = parse_elements(inpt[2:])
            assert remnant and remnant[0] == ']', 'parse error: unclosed character class (base)'
            return ((NCLS,) + elements[1:]), remnant[1:]
        else: # positive character class
            elements, remnant = parse_elements(inpt[1:])
            assert remnant and remnant[0] == ']', 'parse error: unclosed character class (base)'
            return elements, remnant[1:]
    elif inpt[0] in RESERVED:
        # can't raise an exception for this; it's most likely not an error
        # specifically, a boundary (e.g. before a '|' or a ')') will be
        # caught here.
        return None, inpt
    else: # literal
        return (LTRL, inpt[0]), inpt[1:]

# star -> base '*'
# star -> base
def parse_star(inpt, groups):
    b, remnant = parse_base(inpt, groups)
    if b is None: # need to backtrack somewhere up the call stack
        return None, inpt
    elif remnant and remnant[0] == '*': # found *
        return (STAR, b), remnant[1:]
    else: # no *
        return b, remnant

# ccat -> star ccat
# ccat -> None
def parse_ccat(inpt, groups):
    s, remnant = parse_star(inpt, groups)
    if s is None:
        return None, inpt
    else:
        c, new_remnant = parse_ccat(remnant, groups)
        if c is None:
            return s, remnant
        else:
            return (CCAT, s, c), new_remnant

# dsjn -> ccat dprime
def parse_dsjn(inpt, groups):
    c, remnant = parse_ccat(inpt, groups)
    sd, new_remnant = parse_dprime(remnant, groups)
    if c is None and sd is None:
        assert inpt == '', 'egregious parse error (d)'
        return None, inpt
    elif sd is None:
        return c, remnant
    else:
        # assert should only fail for a regexp like "|abc", which is malformed
        assert c is not None, 'parse error: | used without first subexpression'
        return (DSJN, c, sd), new_remnant

# dprime -> '|' ccat dprime
# dprime -> None
def parse_dprime(inpt, groups):
    if inpt == '' or inpt[0] != '|':
        return None, inpt
    else:
        assert inpt[0] == '|', 'egregious parse error (dprime)'
        c, remnant = parse_ccat(inpt[1:], groups)
        assert c is not None, 'parse error: | followed by invalid expression'
        sd, new_remnant = parse_dprime(remnant, groups)
        if sd is None:
            return c, remnant
        else:
            return (DSJN, c, sd), new_remnant

# elements, range, and rprime nodes are used to recognize standard-style
# character classes, such as [A-Za-z0-9]

# elements -> range elements
# elements -> None
def parse_elements(inpt):
    rnge, remnant = parse_range(inpt)
    if rnge is None:
        return None, inpt
    else:
        elements, new_remnant = parse_elements(remnant)
        if elements is None:
            return rnge, remnant
        else:
            return (((CLSS, rnge[1] | elements[1]) + rnge[2:] + elements[2:]),
                    new_remnant)

# range -> literal rprime
# range -> None
def parse_range(inpt):
    assert inpt != '', 'parse error: unclosed character class (range)'
    if inpt[0] == ']':
        return None, inpt
    else:
        if inpt[0] == '/': # escape sequence!
            inpt = inpt[1:]
            assert inpt, 'parse error: pattern terminated during escape sequence'
        begin = inpt[0]
        rprime, remnant = parse_rprime(inpt[1:])
        if rprime is None: # not a range, just a literal
            return (CLSS, {begin}), inpt[1:]
        else:
            return (CLSS, set(), (RNGE, begin, rprime)), remnant

# rprime -> - literal
# rprime -> None
def parse_rprime(inpt):
    assert inpt != '', 'parse error: unclosed character class (rprime)'
    if inpt[0] != '-' or inpt[0:2] == '-]':
        # - at the end of a class is taken literally
        return None, inpt
    else:
        assert len(inpt) >= 2, 'parse error: unclosed character class (rprime)'
        return inpt[1], inpt[2:]
