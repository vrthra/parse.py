#!/usr/bin/env python3
import sys
import functools
import re
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

class PEGParser:
    def __init__(self, grammar): self.grammar = grammar

    def literal_match(self, part, text, tfrom):
        if not text[tfrom:].startswith(part): return None
        return (part, (tfrom + len(part), None))

    @functools.lru_cache(maxsize=None)
    def unify_line(self, rule, text, tfrom):
        def is_symbol(v): return v[0] == '$'

        parts = [s for s in re.split(RE_NONTERMINAL, rule) if s]
        results = []
        for part in parts:
            res = self.unify_key(part, text, tfrom) if is_symbol(part) else self.literal_match(part, text, tfrom)
            if not res: return None
            results.append(res)
            key, (tfrom, ret) = res
        return (tfrom, results)

    @functools.lru_cache(maxsize=None)
    def unify_key(self, key, text, tfrom=0):
        rules = self.grammar[key]
        rets = (self.unify_line(rule, text, tfrom) for rule in rules)
        ret = next((ret for ret in rets if ret), None)
        return (key, ret) if ret else None

def using(fn):
    with fn as f: yield f

def main(args):
    to_parse, = [f.read().strip() for f in using(open(args[1], 'r'))]

    grammar = term_grammar
    if len(args) > 2:
        grammarstr, = [f.read().strip() for f in using(open(args[2], 'r'))]
        grammar = json.loads(grammarstr)
    result = PEGParser(grammar).unify_key('$START', to_parse)
    print(result)

if __name__ == '__main__':
    main(sys.argv)
