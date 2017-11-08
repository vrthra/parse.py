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



def initialize(grammar, start):
    pline.PLine.init_cache(g, follow(grammar, start, {}))
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
