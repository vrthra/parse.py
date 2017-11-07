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

def gkeys(grammar):
    return [k for k,v in grammar]

RE_NONTERMINAL = re.compile(r'(\$[a-zA-Z_]*)')


def match_literal(rule, stack, lookahed):
    # get len of rule
    rulelen = len(rule)
    # get that may out of the stack.
    if len(stack) < rulelen: return ()
    vstack = stack[-rulelen:]
    for a,b in zip(vstack, rule):
       if a != b: return ()
    del stack[-rulelen:]
    return vstack




def match(rule, stack, lookahead):
    if '$' not in rule: return match_literal(rule, stack)
    vals = re.findall(RE_NONTERMINAL, rule)
    vlen = len(vals)
    if vlen > len(stack): return ()
    vstack = (stack+ lookahead)[-vlen:]

    for a,b in zip(vstack, vals):
        if a != b: return ()
    del stack[-vlen:]
    return vstack



def do_reduce(expr_stack, lookahead):
    if not expr_stack: return False
    for k,rules in term_grammar.items():
        for rule in rules:
           m = match(rule, expr_stack, lookahead)
           if m: # v should be more than key
               expr_stack.append(k) # should push (k, m.matched)
               return True

def parse(grammar, input_text):
    expr_stack = []
    tokens = list(input_text)
    token_num = 0
    while tokens or len(expr_stack) > 1:
       if not do_reduce(expr_stack, tokens[-1:] or []) and tokens:
            next_token, *tokens = tokens
            expr_stack.append(next_token) # shift

    assert len(expr_stack) == 1
    return expr_stack[0]

def is_nullable(tok, grammar):
    if is_terminal(tok): return False
    rules = grammar[tok]
    for rule in rules:
        if not rule: return True
        else:
           t, *tok = PLine.split_production_str(rule)
           if is_nullable(t, grammar): return True
    return False

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

    >>> sorted(follow('$E', g, '$E'))
    ['$', ')']
    >>> sorted(follow('$Ex', g, '$E'))
    ['$', ')']
    >>> sorted(follow('$T', g, '$E'))
    ['$', ')', '+']
    >>> sorted(follow('$Tx', g, '$E'))
    ['$', ')', '+']
    >>> sorted(follow('$F', g, '$E'))
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
    return fdict[tok]



# p0, p1, p2, ..
def construct_production_table(grammar):
    productions = []
    i = 0
    for key, rules in gkeys(grammar):
        for rule in rules:
           vals = re.findall(RE_NONTERMINAL, rule)
           productions.append(('p%d' % i,  (key, vals)))
           i += 1
    return productions

def get_next_dfa_state(state, keys):
    for key in keys:
        for (k, r, cursor) in state:
            # check if the key is what is at the cursor in the rules.
            if r[cursor] == key:
                yield (k, r, cursor+1)
        # advance by one

def get_next_dfa_states(dfa_states, keys):
    for state in dfa_states:
        yield from get_next_dfa_state(state, keys)

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

def get_productions(nonterminal, cursor, lookahead, grammar):
    """
    Get the next level of productions from the rules of this non terminal.
    >>> grammar = term_grammar
    >>> get_productions('$START', 0, '$', grammar)
    [PLine('$START', ['$EXPR'], 0, '$')]
    >>> get_productions('$EXPR', 0, '$', grammar)
    [PLine('$EXPR', ['$EXPR', ' + ', '$TERM'], 0, '$'), PLine('$EXPR', ['$EXPR', ' - ', '$TERM'], 0, '$'), PLine('$EXPR', ['$TERM'], 0, '$')]
    """
    prod_strs = grammar[nonterminal]
    plines = []
    for pstr in prod_strs:
        tokens = PLine.split_production_str(pstr)
        pl = PLine(nonterminal, tokens, cursor, lookahead, grammar)
        plines.append(pl)
    return plines


class PLine:
    def __init__(self, key, tokens, cursor, lookahead, grammar):
        self.key,self.tokens,self.cursor,self.lookahead,self.grammar=key,tokens,cursor,lookahead,grammar

    def __repr__(self):
        return 'PLine' + str((self.key, self.tokens, self.cursor, self.lookahead))

    def split_production_str(rule):
        """
        >>> PLine.split_production_str('ac $abc bd')
        ['ac ', '$abc', ' bd']
        >>> PLine.split_production_str('1')
        ['1']
        """
        if '$' not in rule: return [rule]
        return [f for f in re.split(RE_NONTERMINAL, rule) if f]

    def at(self, cursor):
        return self.tokens[cursor]

    def get_terminals(self, cursor):
        tok = self.at(cursor)
        log.debug(tok)
        if is_terminal(tok):
            return set([tok])
        else:
            return set(self._get_terminal(tok))

    def _get_terminal(self, tok):
        terminals = []
        for rule in self.grammar[tok]:
            t,*_rest = PLine.split_production_str(rule)
            if is_terminal(t):
                terminals.append(t)
            else:
                terminals += self._get_terminal(t)
        return terminals


class State:
    def __init__(self, plines, cursor):
        self.plines, self.cursor = plines, cursor

    @classmethod
    def construct_initial_state(cls, grammar):
        """
        >> grammar = term_grammar
        >> State.construct_initial_state(grammar)
        """
        key = '$START'
        production_str = grammar[key][0]
        tokens = PLine.split_production_str(production_str) + [Dollar()]
        cursor = 0
        lookahead = Q()
        plines = [PLine(key=key, tokens=tokens, cursor=0, lookahead=lookahead, grammar=grammar)]
        cont = True
        while cont:
            cont = False
            new_plines = []
            for p in plines:
                if is_nonterminal(p.at(cursor)):
                    la = set(p.get_terminals(cursor+1))
                    new_plines += get_productions(nonterminal=p.at(cursor), cursor=cursor, lookahead=la, grammar=grammar)
                    # need to register
                    cont = True
                else: pass # nothing to be done for this
            plines = new_plines
        return cls(plines, cursor)

def construct_states(grammar):
    state1 = State.construct_initial_state(grammar)
    return state1



def using(fn):
    with fn as f: yield f

def main(args):
    to_parse, = [f.read().strip() for f in using(open(args[1], 'r'))]
    grammar = term_grammar
    result = construct_states(grammar)
    print(result)

if __name__ == '__main__':
    main(sys.argv)
