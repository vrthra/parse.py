#!/usr/bin/env python3
import sys
import re
import collections
import json

term_grammar = {
    "$START":
        ["$EXPR"],

    "$EXPR":
        ["$TERM + $EXPR", "$TERM - $EXPR", "$TERM"],
    
    "$TERM":
        ["$FACTOR * $TERM", "$FACTOR / $TERM", "$FACTOR"],
    
    "$FACTOR":
        ["+$FACTOR", "-$FACTOR", "($EXPR)", "$INTEGER.$INTEGER", "$INTEGER"],

    "$INTEGER":
        ["$DIGIT$INTEGER", "$DIGIT"],

    "$DIGIT":
        ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
}

RE_NONTERMINAL = re.compile(r'(\$[a-zA-Z_]*)')

class ParseResult:
    def __str__(self):
        if self.val == None: return self.key
        return '(' + ''.join([str(i) for i in self.val]) + ')'

    def __repr__(self):
        if self.val == None: return self.key
        return '<%s %s>' % (self.key, ''.join([repr(i) for i in self.val]))

class NoParse(ParseResult):
    def __bool__(self): return False

class KeyMatch(ParseResult):
    def __init__(self, key, frm, til, val): self.key, self.frm, self.til, self.val = key, frm, til, val

class RuleMatch(ParseResult):
    def __init__(self, val, till): self.val, self.till = val, till

def is_symbol(x): return x[0] == '$'

def memoize(targnum):
    def fn_wrap(function):
        memo = {}
        def wrapper(*args):
            lst = (args[i] for i in targnum)
            if lst in memo: return memo[lst]
            rv = function(*args)
            memo[lst] = rv
            return rv
        return wrapper
    return fn_wrap

def unify_line(rule, grammar, text, tfrom):
    parts = [s for s in re.split(RE_NONTERMINAL, rule) if s]
    results = []
    while parts:
        part, *parts = parts
        if is_symbol(part):
            res = unify_key(part, grammar, text, tfrom)
            if not res: return RuleMatch(val=[], till=0)
            results.append(res)
            tfrom = res.til
        else:
            if text[tfrom:].startswith(part):
                till = tfrom + len(part)
                results.append(KeyMatch(part, tfrom, till, None))
                tfrom = till
            else: return RuleMatch(val=[], till=0)
    return RuleMatch(val=results, till=tfrom)


# returns (key, from, till,val)}
@memoize((0,2,3))
def unify_key(key, grammar, text, tfrom=0):
    rules = grammar[key]

    # PEG -- try by order.
    for rule in rules:
        ret = unify_line(rule, grammar, text, tfrom)
        if not ret.val: continue # PEG
        return KeyMatch(key, tfrom, ret.till, ret.val)
    return NoParse()

def using(fn):
    with fn as f: yield f

def main(args):
    to_parse, = [f.read().strip() for f in using(open(args[1], 'r'))]

    grammar = term_grammar
    if len(args) > 2:
        grammarstr, = [f.read().strip() for f in using(open(args[2], 'r'))]
        grammar = json.loads(grammarstr)
    result = unify_key('$START', grammar, to_parse)
    print(result)

if __name__ == '__main__':
    main(sys.argv)
