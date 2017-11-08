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

def parse(input_text, grammar, registry):
    """
    >>> g = {}
    >>> g['$E']  = ['$T$Ex']
    >>> g['$Ex'] = ['+$T$Ex','']
    >>> g['$T'] = ['$F$Tx']
    >>> g['$Tx'] = ['*$F$Tx', '']
    >>> g['$F'] = ['($E)', '11']
    >>> State.construct_states(g, start='$E')
    >>> text = "11"
    >>> parse(text, g, State.registry)
    """
    expr_stack = []
    state_stack = [registry[0]]
    tokens = list(input_text)
    while tokens or len(expr_stack) > 1:
        next_token, *tokens = tokens
        # use the next_token on the state stack to decide what to do.
        top_stack = state_stack[0]
        nxt_state = top_stack.shift_to(next_token)
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
                t = top_stack.go_to(pline.key)
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

def follow(tok, grammar, start='$START', fdict={}):
    """
    >>> g = {}
    >>> g['$E']  = ['$T$Ex']
    >>> g['$Ex'] = ['+$T$Ex','']
    >>> g['$T'] = ['$F$Tx']
    >>> g['$Tx'] = ['*$F$Tx', '']
    >>> g['$F'] = ['($E)', '11']
    >>> fdict = {}
    >>> sorted(follow('$E', g, '$E', fdict))
    ['$', ')']
    >>> sorted(follow('$Ex', g, '$E', fdict))
    ['$', ')']
    >>> sorted(follow('$T', g, '$E', fdict))
    ['$', ')', '+']
    >>> sorted(follow('$Tx', g, '$E', fdict))
    ['$', ')', '+']
    >>> sorted(follow('$F', g, '$E', fdict))
    ['$', ')', '*', '+']
    """
    if fdict.get(tok): return fdict[tok]
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
    return fdict[tok]

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
    registry = {}
    def __init__(self, key, tokens, cursor, lookahead=set(), grammar=None):
        self.key,self.tokens,self.cursor,self.lookahead,self.grammar=key,tokens,cursor,lookahead,grammar

    @classmethod
    def register(cls, oid, obj):
        cls.registry[obj] = oid

    def production_number(self):
        return registry[self]

    def __repr__(self):
        return 'PLine: %s -> %s cursor: %s %s' % (self.key, ''.join(self.tokens), self.cursor, '@' + ''.join(sorted(self.lookahead)))

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
        >>> g['$E'] = ['$T', '($E)']
        >>> g['$T'] = ['1', '+$T', '$T+1']
        >>> pl = PLine.split_production_str('$E')
        >>> c = State.lr0_closure(PLine(key='$S', tokens=pl, cursor=0), 0, g)
        >>> c[0]
        PLine('$S', ['$E'], 0, '@')
        >>> c[0].advance()
        ('', None)

        >>> c[2]
        PLine('$E', ['(', '$E', ')'], 0, '@')
        >>> c[2].advance()
        ('(', PLine('$E', ['(', '$E', ')'], 1, '@'))
        """

        if self.cursor + 1 >= len(self.tokens):
            return '', None
        token = self.at(self.cursor)
        return token, PLine(self.key, self.tokens, self.cursor+1, self.lookahead, self.grammar)

    def at(self, cursor):
        return self.tokens[cursor]

class State:
    counter = 0
    registry = {}
    @classmethod
    def reset(cls):
        cls.counter = 0
        cls.registry = {}

    def __init__(self, plines, cursor):
        self.plines, self.cursor = plines, cursor
        self.shifts = {}
        self.go_tos = {}
        self.i = State.counter
        State.counter += 1
        State.registry[self.i] = self


    def __str__(self):
        return "State(%s): cursor:%s %s" % (self.i, self.cursor, ' '.join([str(i) for i in self.plines]))

    def __repr__(self): return str(self)

    @staticmethod
    def lr0_closure(start, cursor, grammar):
        """
        >>> g = {}
        >>> g['$S'] = ['$E']
        >>> g['$E'] = ['$T', '($E)']
        >>> g['$T'] = ['1', '+$T', '$T+1']
        >>> pl = PLine.split_production_str('$E')
        >>> c = State.lr0_closure(PLine(key='$S', tokens=pl, cursor=0), 0, g)
        >>> c[0]
        PLine('$S', ['$E'], 0, '@')
        >>> c[1]
        PLine('$E', ['$T'], 0, '@')
        >>> c[2]
        PLine('$E', ['(', '$E', ')'], 0, '@')
        >>> c[3]
        PLine('$T', ['1'], 0, '@')
        >>> c[4]
        PLine('$T', ['+', '$T'], 0, '@')
        >>> c[5]
        PLine('$T', ['$T', '+1'], 0, '@')
        """
        # get non-terminals following start.cursor
        # a) Add the item itself to the closure
        pline_counter = 0
        closure = [start]
        items = [start]
        seen = set()
        seen.add(start.key)
        PLine.register(pline_counter, start)
        pline_counter += 1
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
                    tokens = PLine.split_production_str(ps)
                    pl = PLine(key=token, tokens=tokens, cursor=0)
                    items.append(pl)
                    closure.append(pl)
                    PLine.register(pline_counter, pl)
                    pline_counter += 1
                    seen.add(pl.key)
        return closure

    @staticmethod
    def to_lr1(lr0_items, start, grammar, fdict):
        """
        attach lookahead from follow sets to each item.
        >>> g = {}
        >>> g['$S'] = ['$E']
        >>> g['$E'] = ['$T', '($E)']
        >>> g['$T'] = ['1', '+$T', '$T+1']
        >>> pl = PLine.split_production_str('$E')
        >>> fdict = {}
        >>> c = State.to_lr1(State.lr0_closure(PLine(key='$S', tokens=pl, cursor=0), 0, g), '$S', g, fdict)
        >>> c[0]
        PLine('$S', ['$E'], 0, '@$')
        >>> c[1]
        PLine('$E', ['$T'], 0, '@$)')
        >>> c[2]
        PLine('$E', ['(', '$E', ')'], 0, '@$)')
        >>> c[3]
        PLine('$T', ['1'], 0, '@$)+1')
        >>> c[4]
        PLine('$T', ['+', '$T'], 0, '@$)+1')
        >>> c[5]
        PLine('$T', ['$T', '+1'], 0, '@$)+1')
        """
        for item in lr0_items:
            item.lookahead = follow(item.key, grammar, start, fdict)
        return lr0_items

    @classmethod
    def construct_initial_state(cls, grammar, start='$START'):
        """
        >>> g = {}
        >>> g['$S'] = ['$E']
        >>> g['$E'] = ['$T', '($E)']
        >>> g['$T'] = ['1', '+$T', '$T+1']
        >>> s = State.construct_initial_state(g, start='$S')
        >>> s.plines[0]
        PLine('$S', ['$E', .$], 0, '@$')
        >>> s.plines[1]
        PLine('$E', ['$T'], 0, '@$)')
        >>> s.plines[2]
        PLine('$E', ['(', '$E', ')'], 0, '@$)')
        >>> s.plines[3]
        PLine('$T', ['1'], 0, '@$)+1')
        >>> s.plines[4]
        PLine('$T', ['+', '$T'], 0, '@$)+1')
        >>> s.plines[5]
        PLine('$T', ['$T', '+1'], 0, '@$)+1')
        >>> State.reset()
        """
        key = start
        production_str = grammar[key][0]
        tokens = PLine.split_production_str(production_str) + [Dollar()]
        cursor = 0
        lr0_items = State.lr0_closure(start=PLine(key=key, tokens=tokens, cursor=cursor), cursor=0, grammar=grammar)
        fdict = {}
        lr1_items = State.to_lr1(lr0_items, start=start, grammar=grammar, fdict=fdict) # add the look ahead.
        return cls(lr1_items, cursor)
    
    def go_to(self, token):
        if self.go_tos.get(token): return self.go_tos[token]
        new_plines = []
        for pline in self.plines:
            tadv, new_pline = pline.advance()
            if token == tadv:
                new_plines.append(new_pline)
        if not new_plines: return None
        s = State(new_plines, self.cursor + 1)
        self.go_tos[token] = s
        return s

    def shift_to(self, token):
        """
        >>> g = {}
        >>> g['$S'] = ['$E']
        >>> g['$E'] = ['$T', '($E)']
        >>> g['$T'] = ['1', '+$T', '$T+1']
        >>> s = State.construct_initial_state(g, start='$S')
        >>> s.shift_to('$T')
        State(1): cursor:1 PLine('$T', ['$T', '+1'], 1, '@$)+1')
        >>> s.shift_to('$E')
        State(2): cursor:1 PLine('$S', ['$E', .$], 1, '@$')
        >>> State.reset()
        """
        if self.shifts.get(token): return self.shifts[token]
        new_plines = []
        for pline in self.plines:
            tadv, new_pline = pline.advance()
            if token == tadv:
                new_plines.append(new_pline)
        if not new_plines: return None
        s = State(new_plines, self.cursor + 1)
        self.shifts[token] = s
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
        >>> s = State.construct_states(g, '$S')
        >>> len(s.shifts)
        0
        >>> len(s.go_tos)
        2
        >>> s.shift_to('$T')
        State(4): cursor:1 PLine('$E', ['$T', ' + ', '$E'], 1, '@$')
        >>> s.shift_to('$E')
        State(5): cursor:1 PLine('$S', ['$E', .$], 1, '@$')
        >>> len(State.registry)
        6
        >>> State.reset()
        """
        state1 = State.construct_initial_state(grammar, start)
        states = [state1]
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

def using(fn):
    with fn as f: yield f

my_grammar = {}
my_grammar['$E']  = ['$T$Ex']
my_grammar['$Ex'] = ['+$T$Ex','']
my_grammar['$T'] = ['$F$Tx']
my_grammar['$Tx'] = ['*$F$Tx', '']
my_grammar['$F'] = ['($E)', '11']

def main(args):
    to_parse, = [f.read().strip() for f in using(open(args[1], 'r'))]
    grammar = my_grammar
    State.construct_states(grammar, start='$E')
    parse(to_parse, grammar, State.registry)

if __name__ == '__main__':
    main(sys.argv)
