#!/usr/bin/env python3
# vim: set expandtab:
import sys
import re
import collections
import logging as log
log.basicConfig( stream=sys.stdout, level=log.DEBUG )

calc_grammar = [
    ("$START", ["$EXPR"]),

    ("$EXPR", ["$EXPR + $TERM", "$EXPR - $TERM", "$TERM"]),

    ("$TERM", ["$TERM * $FACTOR", "$TERM / $FACTOR", "$FACTOR"]),

    ("$FACTOR", ["+$FACTOR", "-$FACTOR", "($EXPR)", "$INTEGER", "$INTEGER.$INTEGER"]),

    ("$INTEGER", ["$INTEGER$DIGIT", "$DIGIT"]),

    ("$DIGIT", ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"])
]

term_grammar = dict(calc_grammar)

RE_NONTERMINAL = re.compile(r'(\$[a-zA-Z_]*)')
def et(v): return v.replace("\t", " ").replace("\n", " ")

def parse(input_text, grammar, registry):
    """
    >>> g = {}
    >>> g['$S']  = ['$E']
    >>> g['$E']  = ['$T$Ex']
    >>> g['$Ex'] = ['+$T$Ex','']
    >>> g['$T'] = ['$F$Tx']
    >>> g['$Tx'] = ['*$F$Tx', '']
    >>> g['$F'] = ['($E)', '11']

    TODO
    >> State.construct_states(g, start='$S')
    >> text = "11"
    >> parse(text, g, State.registry)
    """
    expr_stack = []
    state_stack = [registry[0]]
    tokens = list(input_text)
    while tokens or len(expr_stack) > 1:
        next_token, *tokens = tokens
        # use the next_token on the state stack to decide what to do.
        top_stack = state_stack[0]
        nxt_state = top_stack.shift[next_token]
        if nxt_state:
            # this means we can shift.
            expr_stack.append(next_token)
            state_stack.append(nxt_state)
        else: # TODO go_tos
            pline = top_stack.can_reduce(next_token)
            if pline:
                # pop the plines' rhs symbols off the stack
                pnum = len(pline.tokens)
                popped = expr_stack[-pnum:]
                expr_stack = expr_stack[:-pnum]
                # push the lhs symbol of pline
                expr_stack.append(pline.key)
                # pop the same number of states.
                state_stack = state_stack[:-pnum]
                t = top_stack.go_tos[pline.key]
                assert t is not None
                state_stack.append(t) # XXX null t here.
            else:
                if next_token == '$' and state.accept():
                    break
                else:
                    raise Exception("Can not accept %s" % next_token)

    assert len(expr_stack) == 1
    return expr_stack[0]

def first(tok, grammar):
    """
    >>> g = {}
    >>> g['$E']  = ['$T$Ex']
    >>> g['$Ex'] = ['+$T$Ex','']
    >>> g['$T'] = ['$F$Tx']
    >>> g['$Tx'] = ['*$F$Tx', '']
    >>> g['$F'] = ['($E)', '11']
    >>> sorted(first('$E', g))
    ['(', '1']
    >>> sorted(first('$Ex', g))
    ['', '+']
    >>> sorted(first('$T', g))
    ['(', '1']
    >>> sorted(first('$Tx', g))
    ['', '*']
    >>> sorted(first('$F', g))
    ['(', '1']

    >>> grammar = term_grammar
    >>> first('+', grammar)
    {'+'}
    >>> sorted(first('$DIGIT', grammar))
    ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    >>> new_g = grammar
    >>> new_g['$X'] = ['$DIGIT', '']
    >>> sorted(first('$X', new_g))
    ['', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    """
    # If X is a terminal then First(X) is just X!
    if is_terminal(tok): return set(tok)
    res = set()
    for rule in grammar[tok]:
        if not rule:
            # If there is a Production X -> ε then add ε to first(X)
            res |= set([''])
        else:
            # If there is a Production X -> Y1Y2..Yk then add first(Y1Y2..Yk) to first(X)
            tokens = PLine.split_production_str(rule)
            add_empty = True
            for t in tokens:
                # First(Y1Y2..Yk) is either
                # First(Y1) (if First(Y1) doesn't contain ε)
                r = first(t, grammar)
                if '' not in r:
                    res |= r
                    add_empty = False
                    break
                else:
                    # OR First (Y1Y2..Yk) is everything in First(Y1) <except for ε > as well as everything in First(Y2..Yk)
                    r.remove('')
                    res |= r

                # If First(Y1) First(Y2)..First(Yk) all contain ε then add ε to First(Y1Y2..Yk) as well.
            if add_empty:
                res |= set([''])
    return res

def follow(grammar, start='$START', fdict={}):
    """
    >>> g = {}
    >>> g['$E']  = ['$T$Ex']
    >>> g['$Ex'] = ['+$T$Ex','']
    >>> g['$T'] = ['$F$Tx']
    >>> g['$Tx'] = ['*$F$Tx', '']
    >>> g['$F'] = ['($E)', '11']
    >>> fdict = follow(g, '$E', {})
    >>> sorted(fdict['$E'])
    ['$', ')']
    >>> sorted(fdict['$Ex'])
    ['$', ')']
    >>> sorted(fdict['$T'])
    ['$', ')', '+']
    >>> sorted(fdict['$Tx'])
    ['$', ')', '+']
    >>> sorted(fdict['$F'])
    ['$', ')', '*', '+']
    """
    # First put $ (the end of input marker) in Follow(S) (S is the start symbol)
    fdict = fdict or {k:set() for k in grammar.keys()}

    updates = []

    fdict[start] |= {'$'}
    for key in sorted(grammar.keys()):
        for rule in grammar[key]:
            tokens = PLine.split_production_str(rule)
            A = key
            for i, B in enumerate(tokens):
                if not B: continue
                if is_nonterminal(B):
                    if (i + 1) != len(tokens):
                        # If there is a production A → aBb, then everything in FIRST(b) except for ε is placed in FOLLOW(B).
                        # If there is a production A → aBb, where FIRST(b) contains ε, then everything in FOLLOW(A) is in FOLLOW(B)
                        b = tokens[i+1]
                        fb = first(b, grammar)
                        if '' in fb:
                            updates.append((B,A))
                            fdict[B] |= fdict[A]
                            fb.remove('')
                        fdict[B] |= fb
                    else: # if B is the end.
                        # If there is a production A → aB, then everything in FOLLOW(A) is in FOLLOW(B)
                        fdict[B] |= fdict[A]
                        updates.append((B,A))

    cont = True
    while cont:
        cont = False
        for k,v in updates:
            val= (fdict[v] - fdict[k])
            if val:
               cont = True
               fdict[k] |= val
    return fdict

class Token: pass
class Dollar(Token):
    def __str__(self): return '.$'
    def __repr__(self): return str(self)
class Q(Token):
    def __str__(self): return '.?'
    def __repr__(self): return str(self)

def is_nonterminal(val):
    """
    >>> is_nonterminal('$START')
    True
    >>> is_nonterminal('+')
    False
    >>> is_nonterminal(Dollar())
    False
    >>> is_nonterminal(Q())
    False
    """
    if type(val) in [Dollar, Q]: return False
    if not val: return False
    return val[0] == '$'

def is_terminal(val):
    """
    >>> is_terminal('$START')
    False
    >>> is_terminal('+')
    True
    """
    return not is_nonterminal(val)

def symbols(grammar):
    all_symbols = set()
    for key in sorted(grammar.keys()):
        rules = grammar[key]
        for rule in rules:
            elts = PLine.split_production_str(rule)
            all_symbols |= set(elts)
    return all_symbols


class PLine:
    cache = {}
    counter = 0
    fdict = None
    def __init__(self, key, production, cursor=0, lookahead=set(), pnum=0):
        self.key,self.production,self.cursor,self.lookahead = key,production,cursor,lookahead
        self.tokens = PLine.split_production_str(self.production)
        self.pnum = 0

    @classmethod
    def init_cache(cls, grammar, fdict):
        pnum = PLine.counter
        PLine.fdict = fdict
        for key in grammar.keys():
            for production in grammar[key]:
                PLine.cache[(key, production, 0)] = PLine(key, production, 0, lookahead=fdict[key])
                PLine.counter += 1
        return len(PLine.cache.keys())

    @classmethod
    def get(cls, key, production, cursor):
        val = PLine.cache.get((key, production, cursor))
        if val: return val

        seed = PLine.cache.get((key, production, 0))
        val = cls(key, production, cursor, seed.lookahead, seed.pnum)
        PLine.cache[(key, production, cursor)] = val

        return val

    @classmethod
    def from_seed(cls, obj, cursor):
        return PLine.get(obj.key, obj.production, cursor)

    def production_number(self):
        return self.pnum

    def __repr__(self):
        return "[p%s]: %s -> %s \tcursor: %s %s" % (self.production_number(),
                self.key, ''.join([str(i) for i in self.tokens]), self.cursor, '@' + ''.join(sorted(self.lookahead)))

    def __str__(self):
        return "[p%s]: %s -> %s \tcursor: %s %s" % (self.production_number(),
                self.key, ''.join([str(i) for i in self.tokens]), self.cursor, '@' + ''.join(sorted(self.lookahead)))

    def split_production_str(rule):
        """
        >>> PLine.split_production_str('ac $abc bd')
        ['ac ', '$abc', ' bd']
        >>> PLine.split_production_str('1')
        ['1']
        """
        if '$' not in rule: return [rule]
        return [f for f in re.split(RE_NONTERMINAL, rule) if f]

    def advance(self):
        """
        creates a new pline with cursor incremented by one
        >>> g = {}
        >>> g['$S'] = ['$E']
        >>> g['$E'] = ['$T + $E', '$T']
        >>> g['$T'] = ['1']
        >>> PLine.init_cache(g, State.update_follow_dicts(g, '$S', {}))
        4
        >>> c = State.lr1_closure([PLine.get(key='$S', production='$E', cursor=0)], 0, g)
        >>> et(str(c[0]))
        '[p0]: $S -> $E  cursor: 0 @'
        >>> et(str(c[0].advance()))
        "('$E', [p0]: $S -> $E  cursor: 1 @)"
        >>> et(str(c[1]))
        '[p1]: $E -> $T + $E  cursor: 0 @'
        >>> et(str(c[1].advance()))
        "('$T', [p0]: $E -> $T + $E  cursor: 1 @)"
        >>> et(str(c[2]))
        '[p2]: $E -> $T  cursor: 0 @'
        >>> et(str(c[2].advance()))
        "('$T', [p0]: $E -> $T  cursor: 1 @)"
        """

        if self.cursor >= len(self.tokens):
            return '', None
        token = self.at(self.cursor)
        return token, PLine.from_seed(self, self.cursor+1)
    def at(self, cursor):
        return self.tokens[cursor]

class State:
    counter = 1
    registry = {}
    @classmethod
    def reset(cls):
        cls.counter = 0
        cls.registry = {}

    def __init__(self, plines, cursor, sfrom=None):
        self.plines, self.cursor = plines, cursor
        self.shifts = {}
        self.go_tos = {}
        self.i = State.counter
        if sfrom:
            self.grammar = sfrom.grammar
            self.start = sfrom.start
        State.counter += 1
        State.registry[self.i] = self


    def __str__(self):
        return "State(%s):\n\t%s" % (self.i, "\n".join([str(i) for i in self.plines]))

    def __repr__(self): return str(self)

    @staticmethod
    def lr1_closure(closure, cursor, grammar):
        """
        >>> g = {}
        >>> g['$S'] = ['$E']
        >>> g['$E'] = ['$T + $E', '$T']
        >>> g['$T'] = ['1']
        >>> PLine.init_cache(g, State.update_follow_dicts(g, '$S', {}))
        >>> c = State.lr1_closure([PLine.get(key='$S', production='$E', cursor=0)], 0, g)
        >>> c = [et(str(l)) for l in c]
        >>> len(c)
        4
        >>> c[0]
        '[p0]: $S -> $E  cursor: 0 @'
        >>> c[1]
        '[p0]: $E -> $T + $E  cursor: 0 @$'
        >>> c[2]
        '[p0]: $E -> $T  cursor: 0 @$'
        >>> c[3]
        '[p0]: $T -> 1  cursor: 0 @ $+'
        """
        # get non-terminals following start.cursor
        # a) Add the item itself to the closure
        items = closure[:] # copy
        seen = set()
        for i in items: seen.add(i.key)
        # c) Repeat (b, c) for any new items added under (b).
        while items:
            item, *items = items
            # b) For any item in the closure, A :- α . β γ where the next symbol
            # after the dot is a nonterminal, add the production rules of that
            # symbol where the dot is before the first item
            # (e.g., for each rule β :- γ, add items: β :- . γ
            token = item.at(cursor)
            if token in seen: continue
            if is_nonterminal(token):
                for ps in grammar[token]:
                    pl = PLine.get(key=token, production=ps, cursor=0)
                    items.append(pl)
                    closure.append(pl)
                    seen.add(pl.key)
        return closure

    @staticmethod
    def update_follow_dicts(grammar, start, fdict):
        # we need only non-terminals for follow. For all others, there is no
        # reason to look up.
        return follow(grammar, start, fdict)

    @classmethod
    def construct_initial_state(cls, grammar, start='$START'):
        """
        >>> g = {}
        >>> g['$S'] = ['$E']
        >>> g['$E'] = ['$T + $E', '$T']
        >>> g['$T'] = ['1']
        >>> PLine.init_cache(g, State.update_follow_dicts(g, '$S', {}))
        7
        >>> s = State.construct_initial_state(g, start='$S')
        >>> l = [et(str(l)) for l in s.plines]
        >>> len(l)
        4
        >>> l[0]
        '[p0]: $S -> $E.$  cursor: 0 @$'
        >>> l[1]
        '[p1]: $E -> $T + $E  cursor: 0 @$'
        >>> l[2]
        '[p2]: $E -> $T  cursor: 0 @$'
        >>> l[3]
        '[p3]: $T -> 1  cursor: 0 @ $+'
        >>> State.reset()
        """
        key = start
        production_str = grammar[key][0]
        cursor = 0

        pl = PLine.get(key=key, production=production_str, cursor=0)
        pl.tokens.append(Dollar())

        lr1_items = State.lr1_closure(closure=[pl],
                cursor=0,
                grammar=grammar)

        state =  cls(lr1_items, cursor)
        # seed state
        state.start, state.grammar = start, grammar
        return state

    def go_to(self, token):
        if self.go_tos.get(token): return self.go_tos[token]
        new_plines = []
        for pline in self.plines:
            tadv, new_pline = pline.advance()
            if token == tadv:
                new_plines.append(new_pline)
        if not new_plines: return None
        s = State(plines=new_plines, cursor=(self.cursor + 1), sfrom=self)
        self.go_tos[token] = s
        return s

    def shift_to(self, token):
        """
        >>> g = {}
        >>> g['$S'] = ['$E']
        >>> g['$E'] = ['$T', '($E)']
        >>> g['$T'] = ['1', '+$T', '$T+1']
        >>> PLine.init_cache(g, State.update_follow_dicts(g, '$S', {}))
        >>> s = State.construct_initial_state(g, start='$S')
        >>> et(str(s.shift_to('$T')))
        'State(1):  [p0]: $E -> $T  cursor: 1 @$) [p0]: $T -> $T+1  cursor: 1 @$)+1'
        >>> et(str(s.shift_to('$E')))
        'State(2):  [p0]: $S -> $E.$  cursor: 1 @$'
        >>> State.reset()
        """
        if self.shifts.get(token): return self.shifts[token]
        new_plines = []
        for pline in self.plines:
            tadv, new_pline = pline.advance()
            if token == tadv:
                new_plines.append(new_pline)
        if not new_plines: return None
        # each time we shift, we have to build a new closure, with cursor at 0
        # for the newly added rules.
        s = self.form_closure(new_plines)
        self.shifts[token] = s
        return s

    def form_closure(self, plines):
        closure = State.lr1_closure(closure=plines, cursor=0, grammar=self.grammar)
        s = State(plines=plines, cursor=(self.cursor + 1), sfrom=self)
        return s

    def accept(self):
        for pline in self.plines:
            if pline.at(pline.cursor) == Dollar():
                return True
        return False

    def can_reduce(self, nxt_tok):
        # is the cursor at the end in any of the plines?
        for pline in self.plines:
            if pline.cursor + 1 >= len(pline.tokens):
                res = nxt_tok in pline.lookahead
                if res: return pline
        # return the production number too for this pline
        return None


    @classmethod
    def construct_states(cls, grammar, start='$START'):
        """
        >>> g = {}
        >>> g['$S'] = ['$E']
        >>> g['$E'] = ['$T', '$T + $E']
        >>> g['$T'] = ['1']
        >>> PLine.init_cache(g, State.update_follow_dicts(g, '$S', {}))
        7
        >>> s = State.construct_states(g, '$S')
        >>> len(State.registry)
        6

        >> len(s.shifts) # there should be two shifts
        2
        >> len(s.go_tos) # there should be 4 gotos
        4

        >>> et(str(s.shift_to('$T')))
        'State(6):  [p0]: $E -> $T  cursor: 1 @$ [p0]: $E -> $T + $E  cursor: 1 @$'
        >>> et(str(s.shift_to('$E')))
        'State(7):  [p0]: $S -> $E.$  cursor: 1 @$'
        >>> len(State.registry) # todo -- two of them -- state3, and state4 are dups
        8
        >>> State.reset()
        """

        state1 = State.construct_initial_state(grammar, start)
        states = [state1]
        follow = {}
        while states:
            state, *states = states
            for key in sorted(symbols(grammar)): # needs terminal symbols too.
                if is_terminal(key):
                    new_state = state.shift_to(key)
                    if new_state: states.append(new_state)
                else:
                    new_state = state.go_to(key)
                    if new_state: states.append(new_state)
        return state1

def initialize(grammar, start):
    PLine.init_cache(g, State.update_follow_dicts(grammar, start, {}))
    State.construct_states(grammar, start='$S')
    log.debug("States:")
    for skey in State.registry.keys():
        s = State.registry[skey]
        log.debug(s)
    log.debug('')

def using(fn):
    with fn as f: yield f

my_grammar = {}
my_grammar['$S'] = ['$E']
my_grammar['$E']  = ['$T + $E', '$T']
my_grammar['$T'] = ['11']

def main(args):
    to_parse, = [f.read().strip() for f in using(open(args[1], 'r'))]
    grammar = my_grammar
    initialize(grammar, start)
    parse("11", grammar, State.registry)

if __name__ == '__main__':
    main(sys.argv)
