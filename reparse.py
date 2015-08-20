# Regular expressions consist of literal characters (e.g. "a", or "b")
# joined by the three operations disjunction ("a|b"), concatenation ("ab")
# and Kleene star ("a*"). Intuitively, the grammar defining them looks like:
#   R -> literal
#   R -> R * (Kleene star)
#   R -> R R (concatenation)
#   R -> R | R (disjunction)
# Since this is quite ambiguous, we use a version encoding an explicit
# order of operations (first star, then concatenation, then disjunction):
#   D  -> C D'
#   D' -> | C D'
#   D' -> "" (the empty string)
#   C  -> S C
#   C  -> ""
#   S  -> B *
#   S  -> B
#   B  -> ( D )
#   B  -> literal
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

# Reserved characters. Forward slash is reserved in case we want to implement
# character escapes later.
RESERVED = {'(', ')', '|', '*', '/'}

def parse(inpt):
    tree, remnant = parse_d(inpt)
    assert remnant == '', 'parse error: did not consume entire input - probably found a reserved character out of place'
    return tree

# B -> ( D ) or literal
def parse_b(inpt):
    if inpt == '':
        # this means that a clause somewhere up the call stack needs to be
        # the empty string
        return None, inpt
    elif inpt[0] == '(': # parenthesized regexp
        d, remnant = parse_d(inpt[1:])
        assert remnant and remnant[0] == ')', 'parse error: no closing ) for earlier ('
        return d, remnant[1:]
    elif inpt[0] in RESERVED:
        # can't raise an exception for this; it's most likely not an error
        return None, inpt
    else: # literal
        return (LTRL, inpt[0]), inpt[1:]

# S -> B * or B
def parse_s(inpt):
    b, remnant = parse_b(inpt)
    if b is None: # need to backtrack somewhere up the call stack
        return None, inpt
    elif remnant and remnant[0] == '*': # found *
        return (STAR, b), remnant[1:]
    else: # no *
        return b, remnant

# C -> S C or None
def parse_c(inpt):
    s, remnant = parse_s(inpt)
    if s is None:
        return None, inpt
    else:
        c, new_remnant = parse_c(remnant)
        if c is None:
            return s, remnant
        else:
            return (CCAT, s, c), new_remnant

# D -> C D'
def parse_d(inpt):
    c, remnant = parse_c(inpt)
    sd, new_remnant = parse_dprime(remnant)
    if c is None and sd is None:
        assert inpt == '', 'egregious parse error (d)'
        return None, inpt
    elif sd is None:
        return c, remnant
    else:
        # assert should only fail for a regexp like "|abc", which is malformed
        assert c is not None, 'parse error: | used without first subexpression'
        return (DSJN, c, sd), new_remnant

# D' -> | C D' or None
def parse_dprime(inpt):
    if inpt == '' or inpt[0] != '|':
        return None, inpt
    else:
        assert inpt[0] == '|', 'egregious parse error (dprime)'
        c, remnant = parse_c(inpt[1:])
        assert c is not None, 'parse error: | followed by invalid expression'
        sd, new_remnant = parse_dprime(remnant)
        if sd is None:
            return c, remnant
        else:
            return (DSJN, c, sd), new_remnant
