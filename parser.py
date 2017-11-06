#!/usr/bin/env python3
import sys
import re
import collections

term_grammar = {
    "$START":
        ["$EXPR"],

    "$EXPR":
        ["$EXPR + $TERM", "$EXPR - $TERM", "$TERM"],

    "$TERM":
        ["$TERM * $FACTOR", "$TERM / $FACTOR", "$FACTOR"],

    "$FACTOR":
        ["+$FACTOR", "-$FACTOR", "($EXPR)", "$INTEGER", "$INTEGER.$INTEGER"],

    "$INTEGER":
        ["$INTEGER$DIGIT", "$DIGIT"],

    "$DIGIT":
        ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
}

RE_NONTERMINAL = re.compile(r'(\$[a-zA-Z_]*)')

class ParseResult: pass

class NoParse(ParseResult):
    def __bool__(self): return False

class Parsed(ParseResult):
    def __init__(self, key, frm, til, val): self.key, self.frm, self.til, self.val = key, frm, til, val

    def __str__(self): return '%s[%s]' % (self.key, ''.join([str(i) for i in self.val]))

PResult = collections.namedtuple('PResult', 'val till')

def is_symbol(x): return x[0] == '$'

def unify_line(rule, grammar, text, tfrom):
    parts = [s for s in re.split(RE_NONTERMINAL, rule) if s]
    results = []
    while parts:
        part, *parts = parts
        if is_symbol(part):
            res = unify_key(part, grammar, text, tfrom)
            if not res: return PResult(val=[], till=0)
            results.append(res)
            tfrom = res.til
        else:
            if text[tfrom:].startswith(part):
                till = tfrom + len(part)
                results.append(Parsed(part, tfrom, till, []))
                tfrom = till
            else: return PResult(val=[], till=0)
    return PResult(val=results, till=tfrom)


# returns (key, from, till,val)}
def unify_key(key, grammar, text, tfrom=0):
    rules = grammar[key]

    # PEG -- try by order.
    for rule in rules:
        ret = unify_line(rule, grammar, text, tfrom)
        if not ret.val: continue # PEG
        return Parsed(key, tfrom, ret.till, ret.val)
    return NoParse()

def using(fn):
    with fn as f: yield f

def main(args):
    to_parse, = [f.read().strip() for f in using(open(args[1], 'r'))]
    grammar = term_grammar
    result = unify_key('$START', grammar, to_parse)
    print(result)

if __name__ == '__main__':
    main(sys.argv)
