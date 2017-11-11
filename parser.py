#!/usr/bin/env python3
import sys
import functools
import re
import json

term_grammar = {
        "$START": ["$EXPR"],
        "$EXPR": ["$TERM", "$TERM + $EXPR", "$TERM - $EXPR"],
        "$TERM": ["$FACTOR", "$FACTOR * $TERM", "$FACTOR / $TERM"],
        "$FACTOR": ["$INTEGER", "+$FACTOR", "-$FACTOR", "($EXPR)", "$INTEGER.$INTEGER"],
        "$INTEGER": ["$DIGIT", "$DIGIT$INTEGER"],
        "$DIGIT": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
        }

RE_NONTERMINAL = re.compile(r'(\$[a-zA-Z_]*)')
def is_literal(v): return v[0] != '$'

class Parser:
    def __init__(self, grammar):
        def split(rule): return tuple(s for s in re.split(RE_NONTERMINAL, rule) if s)
        self.grammar = {k:[split(l) for l in rules] for k,rules in grammar.items()}

    def literal_match(self, part, text, tfrom):
        return (tfrom + len(part), part) if text[tfrom:].startswith(part) else None

    def unify_words(self, parts, text, tfrom):
        part, *parts = parts
        for l, p in self.unify_key(part, text, tfrom):
            if not parts:
                yield l, p
            else:
                for l1, s1 in self.unify_words(parts, text, l):
                    yield l1, (p, s1)

    def unify_key(self, part, text, tfrom=0):
        if is_literal(part):
            val = self.literal_match(part, text, tfrom)
            if val:
                yield val
            else:
                raise StopIteration
        else:
            for rule in self.grammar[part]:
                for l, p in self.unify_words(rule, text, tfrom):
                    yield l, (part, p)

def main(args):
    def readall(fn): return ''.join([f for f in open(fn, 'r')]).strip()

    to_parse = '12 + 34 * 4' #readall(args[1])
    grammar = json.loads(readall(args[2])) if len(args) > 2 else term_grammar
    for l,result in Parser(grammar).unify_key('$START', to_parse):
        if l == len(to_parse):
            print(result)

if __name__ == '__main__': main(sys.argv)
