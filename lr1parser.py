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
    state_stack = [registry[1].i]
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
            (action, nxt) = State.registry[state_stack[-1]].hrow[pline.key] # TODO: next_staet shoudl be thehead of pline
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
    # log.debug("States:")
    # for skey in State.registry.keys():
    #    s = State.registry[skey]
    #    log.debug(s)
    # log.debug('')

def using(fn):
    with fn as f: yield f

my_grammar = {}
my_grammar['$START'] = ['$E']
my_grammar['$E']  = ['$T+$E', '$T']
my_grammar['$T'] = ['1']

def main(args):
    to_parse, = [f.read().strip() for f in using(open(args[1], 'r'))]
    grammar = term_grammar
    initialize(grammar, '$START')

    for i in PLine.cache.values():
       if i.cursor == 0:
           print(i.pnum, i)
    print()
    for k,s in State.registry.items():
       print(k, "\t".join(["%s:%s" % (k,v) for k,v in s.hrow.items()]))
    parse(to_parse, grammar, State.registry)

if __name__ == '__main__':
    main(sys.argv)
