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
    def __init__(self, grammar):
        def split(rule): return tuple(s for s in re.split(RE_NONTERMINAL, rule) if s)
        self.grammar = {k:[split(l) for l in rules] for k,rules in grammar.items()}

    def literal_match(self, part, text, tfrom):
        return (tfrom + len(part), (part, [])) if text[tfrom:].startswith(part) else (tfrom, None)

    @functools.lru_cache(maxsize=None)
    def unify_key(self, key, text, tfrom=0):
        rules = self.grammar[key]
        rets = (self.unify_line(rule, text, tfrom) for rule in rules)
        tfrom, res = next((ret for ret in rets if ret[1] is not None), (tfrom, None))
        return (tfrom, (key, res) if res is not None else None)

    @functools.lru_cache(maxsize=None)
    def unify_line(self, parts, text, tfrom):
        def is_symbol(v): return v[0] == '$'

        results = []
        for part in parts:
            tfrom, res = (self.unify_key if is_symbol(part) else self.literal_match)(part, text, tfrom)
            if res is None: return tfrom, None
            results.append(res)
        return tfrom, results

def main(args):
    def readall(fn): return ''.join([f for f in open(fn, 'r')]).strip()

    to_parse = readall(args[1])
    grammar = json.loads(readall(args[2])) if len(args) > 2 else term_grammar
    result = PEGParser(grammar).unify_key('$START', to_parse)
    print(result[1])

if __name__ == '__main__': main(sys.argv)
