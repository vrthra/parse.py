#!/usr/bin/env python3
import sys
import functools
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

class ParseResult: pass

class NoParse(ParseResult):
    def __bool__(self): return False

class KeyMatch(ParseResult):
    def __init__(self, key, frm, til, val): self.key, self.frm, self.til, self.val = key, frm, til, val

    def __str__(self):
        if self.val == None: return self.key
        return '(' + self.key + ' ' + ''.join([str(i) for i in self.val]) + ')'

    def to_json(self):
        return {self.key : [i.to_json() for i in self.val] if self.val else [] }

class RuleMatch(ParseResult):
    def __init__(self, val, till): self.val, self.till = val, till

    def __str__(self):
        return '[' + ''.join([str(i) for i in self.val]) + ']'

    def to_json(self):
        return [i.to_json() for i in self.val]

def is_symbol(x): return x[0] == '$'

class PEGParser:
    def __init__(self, grammar): self.grammar = grammar

    @functools.lru_cache(maxsize=None)
    def unify_line(self, rule, text, tfrom):
        parts = [s for s in re.split(RE_NONTERMINAL, rule) if s]
        results = []
        for part in parts:
            if is_symbol(part):
                res = self.unify_key(part, text, tfrom)
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

    @functools.lru_cache(maxsize=None)
    def unify_key(self, key, text, tfrom=0):
        rules = self.grammar[key]
        rets = (self.unify_line(rule, text, tfrom) for rule in rules)
        ret = next((ret for ret in rets if ret.val), None)
        return KeyMatch(key, tfrom, ret.till, ret.val) if ret else NoParse()

def using(fn):
    with fn as f: yield f

def main(args):
    to_parse, = [f.read().strip() for f in using(open(args[1], 'r'))]

    grammar = term_grammar
    if len(args) > 2:
        grammarstr, = [f.read().strip() for f in using(open(args[2], 'r'))]
        grammar = json.loads(grammarstr)
    result = PEGParser(grammar).unify_key('$START', to_parse)
    print(json.dumps(result.to_json()))

if __name__ == '__main__':
    main(sys.argv)
