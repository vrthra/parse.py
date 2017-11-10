#!/usr/bin/env python3
# vim: set expandtab:
import sys
import re
import collections
import logging as log
from lr1 import *
import pline
from state import *
log.basicConfig( stream=sys.stdout, level=log.DEBUG )

EOF = '\0'

calc_grammar = [
    ("$START", ["$EXPR"]),

    ("$EXPR", ["$EXPR+$TERM", "$EXPR-$TERM", "$TERM"]),

    ("$TERM", ["$TERM*$FACTOR", "$TERM/$FACTOR", "$FACTOR"]),

    ("$FACTOR", ["+$FACTOR", "-$FACTOR", "($EXPR)", "$INTEGER", "$INTEGER.$INTEGER"]),

    ("$INTEGER", ["$INTEGER$DIGIT", "$DIGIT"]),

    ("$DIGIT", ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"])
]

term_grammar = dict(calc_grammar)

RE_NONTERMINAL = re.compile(r'(\$[a-zA-Z_]*)')
def et(v): return v.replace("\t", " ").replace("\n", " ")

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
            tokens = split_production_str(rule) #  $ is being missed here.
            add_empty = True
            for t in tokens:
                # First(Y1Y2..Yk) is either
                # First(Y1) (if First(Y1) doesn't contain ε)
                if t == tok: # recursion
                    continue
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

def split_production_str(rule):
    """
    >>> split_production_str('ac $abc bd')
    ['ac ', '$abc', ' bd']
    >>> split_production_str('1')
    ['1']
    """
    if '$' not in rule: return [rule]
    return [f for f in re.split(RE_NONTERMINAL, rule) if f]

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


    fdict[start] |= {EOF}
    for key in sorted(grammar.keys()):
        for rule in grammar[key]:
            tokens = split_production_str(rule)
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
    >>> is_nonterminal('$')
    False
    >>> is_nonterminal(Q())
    False
    """
    if type(val) in [Q]: return False
    if not val: return False
    return len(val) > 1 and val[0] == '$'

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
            elts = split_production_str(rule)
            all_symbols |= set(elts)
    return all_symbols


class PLine:
    cache = {}
    counter = 0
    fdict = None
    def __init__(self, key, production, cursor=0, lookahead=set(), pnum=0):
        self.key,self.production,self.cursor,self.lookahead = key,production,cursor,lookahead
        self.tokens = split_production_str(self.production)
        self.pnum = pnum

    @classmethod
    def reset(cls):
        PLine.cache.clear()
        PLine.fdict = None
        PLine.counter = 0

    @classmethod
    def init_cache(cls, grammar, fdict):
        """
        Initializes the pline seeds
        >>> g = {}
        >>> g['$S'] = ['$E']
        >>> g['$E'] = ['$T + $E', '$T']
        >>> g['$T'] = ['1']
        >>> PLine.init_cache(g, follow(g, '$S', {}))
        4
        >>> et(str(PLine.cache[('$S', '$E', 0)]))
        '[p2]: $S -> $E  cursor: 0 @$'
        >>> et(str(PLine.cache[('$E', '$T + $E', 0)]))
        '[p0]: $E -> $T + $E  cursor: 0 @$'
        >>> et(str(PLine.cache[('$E', '$T', 0)]))
        '[p1]: $E -> $T  cursor: 0 @$'
        >>> et(str(PLine.cache[('$T', '1', 0)]))
        '[p3]: $T -> 1  cursor: 0 @ $+'
        >>> PLine.reset()
        """
        PLine.fdict = fdict
        for key in sorted(grammar.keys()):
            for production in grammar[key]:
                PLine.cache[(key, production, 0)] = PLine(key, production,
                        cursor=0, lookahead=fdict[key], pnum=PLine.counter)
                PLine.counter += 1
        return len(PLine.cache.keys())

    @classmethod
    def get(cls, key, production, cursor):
        """
        Try to get a predefined pline. If we fail, create new instead.
        """
        val = PLine.cache.get((key, production, cursor))
        if val: return val

        seed = PLine.cache.get((key, production, 0))
        val = PLine(key, production, cursor, seed.lookahead, seed.pnum)
        PLine.cache[(key, production, cursor)] = val

        return val

    @classmethod
    def from_seed(cls, obj, cursor):
        """
        To be used when we need a new pline when we advance the current pline.
        Important: the production rule is unchanged. Only the cursor may be
        different
        """
        return PLine.get(obj.key, obj.production, cursor)

    def production_number(self):
        """
        The number of the original production rule.
        Does not consider cursor location
        """
        return self.pnum

    def __repr__(self):
        return "[p%s]: %s -> %s \tcursor: %s %s" % (self.production_number(),
                self.key, ''.join([str(i) for i in self.tokens]), self.cursor, '@' + ''.join(sorted(self.lookahead)))

    def __str__(self):
        return "[p%s]: %s -> %s \tcursor: %s %s" % (self.production_number(),
                self.key, ''.join([str(i) for i in self.tokens]), self.cursor, '@' + ''.join(sorted(self.lookahead)))

    def advance(self):
        """
        creates a new pline with cursor incremented by one
        >>> PLine.reset()
        >>> g = {}
        >>> g['$S'] = ['$E']
        >>> g['$E'] = ['$T + $E', '$T']
        >>> g['$T'] = ['1']
        >>> PLine.init_cache(g, follow(g, '$S', {}))
        4
        >>> c = lr1_closure([PLine.get(key='$S', production='$E', cursor=0)], 0, g)
        >>> et(str(c[0]))
        '[p2]: $S -> $E  cursor: 0 @$'
        >>> et(str(c[0].advance()))
        "('$E', [p2]: $S -> $E  cursor: 1 @$)"
        >>> et(str(c[1]))
        '[p0]: $E -> $T + $E  cursor: 0 @$'
        >>> et(str(c[1].advance()))
        "('$T', [p0]: $E -> $T + $E  cursor: 1 @$)"
        >>> et(str(c[2]))
        '[p1]: $E -> $T  cursor: 0 @$'
        >>> et(str(c[2].advance()))
        "('$T', [p1]: $E -> $T  cursor: 1 @$)"
        >>> PLine.reset()
        """

        if self.cursor >= len(self.tokens):
            return '', None
        if self.at(self.cursor) == EOF: return '', None
        token = self.at(self.cursor)
        return token, PLine.from_seed(self, self.cursor+1)
    def at(self, cursor):
        if cursor >= len(self.tokens): return None
        return self.tokens[cursor]

def lr1_closure(closure, cursor, grammar):
    """
    >>> g = {}
    >>> g['$S'] = ['$E']
    >>> g['$E'] = ['$T + $E', '$T']
    >>> g['$T'] = ['1']
    >>> PLine.init_cache(g, follow(g, '$S', {}))
    4
    >>> c = lr1_closure([PLine.get(key='$S', production='$E', cursor=0)], 0, g)
    >>> c = [et(str(l)) for l in c]
    >>> len(c)
    4

    TODO: verify if $ belongs here.

    >>> c[0]
    '[p2]: $S -> $E  cursor: 0 @$'
    >>> c[1]
    '[p0]: $E -> $T + $E  cursor: 0 @$'
    >>> c[2]
    '[p1]: $E -> $T  cursor: 0 @$'
    >>> c[3]
    '[p3]: $T -> 1  cursor: 0 @ $+'
    >>> PLine.reset()
    """
    # get non-terminals following start.cursor
    # a) Add the item itself to the closure
    items = closure[:] # copy
    seen = set()
    #for i in items: seen.add(i.key)
    # c) Repeat (b, c) for any new items added under (b).
    while items:
        item, *items = items
        # b) For any item in the closure, A :- α . β γ where the next symbol
        # after the dot is a nonterminal, add the production rules of that
        # symbol where the dot is before the first item
        # (e.g., for each rule β :- γ, add items: β :- . γ
        token = item.at(item.cursor)
        if not token: continue
        if token in seen: continue
        if is_nonterminal(token):
            for ps in grammar[token]:
                pl = PLine.get(key=token, production=ps, cursor=0)
                items.append(pl)
                closure.append(pl)
                seen.add(pl.key)
    return closure

class State:
    counter = 1
    registry = {}
    cache = {}
    def reset():
        PLine.reset()
        State.counter = 1
        State.registry = {}
        State.cache = {}

    def __init__(self, plines, sfrom=None):
        self.plines = plines
        self.shifts = {}
        self.go_tos = {}
        self.i = State.counter
        self.row = []
        self.hrow = {}
        self.note = "*"
        if sfrom:
            self.grammar = sfrom.grammar
            self.start = sfrom.start
        State.counter += 1
        State.registry[self.i] = self
        self.key = ''.join([str(l) for l in plines])
        if State.cache.get(self.key): raise Exception("Cache already has the state. Use State.get")
        State.cache[self.key] = self

    @classmethod
    def get(cls, plines, sfrom=None):
        key = ''.join([str(l) for l in plines])
        val = State.cache.get(key)
        if val: return val
        State.cache[key] = State(plines, sfrom)
        return State.cache[key]



    def __str__(self):
        return "State(%s):\n\t%s" % (self.i, "\n\t".join([str(i) for i in self.plines]))

    def __repr__(self): return str(self)

    @classmethod
    def construct_initial_state(cls, grammar, start='$START'):
        """
        >>> State.reset()
        >>> g = {}
        >>> g['$S'] = ['$E']
        >>> g['$E'] = ['$T + $E', '$T']
        >>> g['$T'] = ['1']
        >>> s = State.construct_initial_state(g, start='$S')
        >>> l = [et(str(l)) for l in s.plines]
        >>> len(l)
        4
        >>> l[0]
        '[p2]: $S -> $E.$  cursor: 0 @$'
        >>> l[1]
        '[p0]: $E -> $T + $E  cursor: 0 @$'
        >>> l[2]
        '[p1]: $E -> $T  cursor: 0 @$'
        >>> l[3]
        '[p3]: $T -> 1  cursor: 0 @ $+'
        >>> State.reset()
        """
        PLine.init_cache(grammar, follow(grammar, start, {}))
        key = start
        production_str = grammar[key][0]

        pl = PLine.get(key=key, production=production_str, cursor=0)

        lr1_items = lr1_closure(closure=[pl], cursor=0, grammar=grammar)
        state =  cls(lr1_items, 0)
        # seed state
        state.start, state.grammar = start, grammar
        return state

    def go_to(self, token):
        """
        >>> State.reset()
        >>> g = {}
        >>> g['$S'] = ['$E']
        >>> g['$E'] = ['$T + $E', '$T']
        >>> g['$T'] = ['1']
        >>> s = State.construct_initial_state(g, start='$S')
        >>> et(str(s.go_to('$T')))
        'State(1 -> [$T] ->  2):  [p0]: $E -> $T + $E  cursor: 1 @$  [p1]: $E -> $T  cursor: 1 @$'
        >>> et(str(s.go_to('1')))
        'None'
        >>> State.reset()
        """
        if self.go_tos.get(token): return self.go_tos[token]
        if is_terminal(token): return None
        new_plines = []
        for pline in self.plines:
            tadv, new_pline = pline.advance()
            if token == tadv:
                new_plines.append(new_pline)
        if not new_plines: return None
        s = self.form_closure(new_plines)
        self.go_tos[token] = s
        s.note = "%s -> [%s] -> " % (self.i,  token)
        return s

    def shift_to(self, token):
        """
        >>> State.reset()
        >>> g = {}
        >>> g['$S'] = ['$E']
        >>> g['$E'] = ['$T + $E', '$T']
        >>> g['$T'] = ['1']
        >>> s = State.construct_initial_state(g, start='$S')
        >>> et(str(s.shift_to('$T')))
        'None'
        >>> et(str(s.shift_to('1')))
        'State(1 -> [1] ->  2):  [p3]: $T -> 1  cursor: 1 @ $+'
        >>> State.reset()
        """
        if self.shifts.get(token): return self.shifts[token]
        if is_nonterminal(token): return None
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
        s.note = "%s -> [%s] -> " % (self.i,  token)
        return s

    def form_closure(self, plines):
        closure = lr1_closure(closure=plines, cursor=0, grammar=self.grammar)
        s = State.get(plines=plines, sfrom=self)
        return s

    def get_reduction(self, nxt_tok):
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
        >>> State.reset()
        >>> g = {}
        >>> g['$S'] = ['$E']
        >>> g['$E'] = ['$T', '$T + $E']
        >>> g['$T'] = ['1']
        >>> s = State.construct_states(g, '$S')
        >>> len(State.registry)
        6

        >> len(s.shifts) # there should be two shifts
        2
        >> len(s.go_tos) # there should be 4 gotos
        4

        >>> et(str(s.shift_to('$T')))
        'None'
        >>> et(str(s.go_to('$T')))
        'State(5 -> [$T] ->  3):  [p0]: $E -> $T  cursor: 1 @$  [p1]: $E -> $T + $E  cursor: 1 @$'
        >>> et(str(s.go_to('$E')))
        'State(1 -> [$E] ->  2):  [p2]: $S -> $E  cursor: 1 @$'
        >>> len(State.registry) # todo -- two of them -- state3, and state4 are dups
        6
        >>> State.reset()
        """

        state1 = State.construct_initial_state(grammar, start)
        states = [state1]
        follow = {}
        all_states = set()
        seen = set()
        while states:
            state, *states = states
            if state.i in seen: continue
            seen.add(state.i)
            all_states.add(state)
            sym = symbols(grammar)
            for key in sorted(sym): # needs terminal symbols too.
                if is_terminal(key):
                    new_state = state.shift_to(key)
                    if new_state: # and new_state.i not in seen:
                        states.append(new_state)
                        state.hrow[key] = ('Shift', new_state.i)
                    else:
                        state.hrow[key] = ('_', None)
                else:
                    new_state = state.go_to(key)
                    if new_state: # and new_state.i not in seen:
                        states.append(new_state)
                        state.hrow[key] = ('Goto', new_state.i)
                    else:
                        state.hrow[key] = ('_', None)

        for state in all_states:
            # for each item, with an LR left of $, add an accept.
            # for each item, with an LR with dot at the end, add a reduce
            # r p
            for line in state.plines:
                if line.at(line.cursor) == EOF:
                    key = EOF 
                    state.hrow[key] = ('Accept', None)
                elif line.cursor + 1 > len(line.tokens):
                    for key in line.lookahead:
                        state.hrow[key] = ('Reduce', line)
        return state1


def parse(input_text, grammar):
    """
    >>> State.reset()
    >>> g = {}
    >>> g['$S']  = ['$E']
    >>> g['$E']  = ['$T+$E', '$T']
    >>> g['$T']  = ['1']
    >>> s1 = State.construct_states(g, start='$S')
    >>> text = "11"
    >>> parse(text, g, State.registry)
    >>> State.reset()
    """
    expr_stack = []
    state_stack = [State.registry[1].i]
    tokens = list(input_text)
    next_token = None
    while True:
        if not next_token:
            if not tokens:
                next_token = EOF
            else:
                next_token, *tokens = tokens
        print("token: %s" % next_token)
        # use the next_token on the state stack to decide what to do.
        (action, nxt) = State.registry[state_stack[-1]].hrow[next_token]
        if action == 'Shift':
            next_state = State.registry[nxt]
            # this means we can shift.
            expr_stack.append(next_token)
            state_stack.append(next_state.i)
            print("shift to (%d):\n%s" % (len(state_stack), next_state))
            next_token = None
        elif action == 'Reduce':
            pline = nxt
            # Remove the matched topmost L symbols (and parse trees and
            # associated state numbers) from the parse stack.
            print("pline:%s" % pline)
            # pop the plines' rhs symbols off the stack
            pnum = len(pline.tokens)
            popped = expr_stack[-pnum:]
            expr_stack = expr_stack[:-pnum]
            # push the lhs symbol of pline
            expr_stack.append(pline.key)
            # pop the same number of states.
            print("pop off:%d" % pnum)
            state_stack = state_stack[:-pnum]
            (action, nxt) = State.registry[state_stack[-1]].hrow[pline.key]
            print("action:%s" % action)
            next_state = State.registry[nxt]
            state_stack.append(next_state.i)
            print("go to (%d):\n%s" % (len(state_stack), next_state))
        elif action == 'Goto':
            next_state = State.registry[nxt]
            state_stack.append(next_state.i)
            print("action:%s" % action)
        elif action == 'Accept':
            print("action:%s" % action)
            break
        else:
            raise Exception("Syntax error")

    assert len(expr_stack) == 1
    return expr_stack[0]



def initialize(grammar, start):
    grammar[start] = [grammar[start][0] + EOF]
    State.construct_states(grammar, start)

def using(fn):
    with fn as f: yield f

def main(args):
    to_parse, = [f.read().strip() for f in using(open(args[1], 'r'))]
    grammar = term_grammar
    initialize(grammar, '$START')
    parse(to_parse, grammar)

if __name__ == '__main__':
    main(sys.argv)
