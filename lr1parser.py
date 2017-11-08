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
    state_stack = [registry[1]]
    tokens = list(input_text)
    next_token = None
    while True:
        if not next_token:
            next_token, *tokens = tokens
        print("token: %s" % next_token)
        # use the next_token on the state stack to decide what to do.
        next_state = state_stack[0].shift_to(next_token)
        if next_state:
            # this means we can shift.
            expr_stack.append(next_token)
            state_stack.append(next_state)
            print("shift to (%d):\n%s" % (len(state_stack), next_state))
            next_token = None
        else: # TODO go_tos
            pline = state_stack[0].can_reduce(next_token)
            if pline:
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
                next_state = state_stack[0].go_tos[pline.key] # TODO: next_staet shoudl be thehead of pline
                assert next_state is not None
                state_stack.append(next_state) # XXX null t here.
                print("go to (%d):\n%s" % (len(state_stack), next_state))
            else:
                if state_stack[0].accept():
                    break
                else:
                    raise Exception("Can not accept %s" % next_token)

    assert len(expr_stack) == 1
    return expr_stack[0]



def initialize(grammar, start):
    State.construct_states(grammar, start='$S')
    # log.debug("States:")
    # for skey in State.registry.keys():
    #    s = State.registry[skey]
    #    log.debug(s)
    # log.debug('')

def using(fn):
    with fn as f: yield f

my_grammar = {}
my_grammar['$S'] = ['$E']
my_grammar['$E']  = ['$T + $E', '$T']
my_grammar['$T'] = ['1']

def main(args):
    to_parse, = [f.read().strip() for f in using(open(args[1], 'r'))]
    grammar = my_grammar
    initialize(grammar, '$S')
    parse("1+1", grammar, State.registry)

if __name__ == '__main__':
    main(sys.argv)
