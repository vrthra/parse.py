#!/usr/bin/env python3
import sys
import time
import re
import collections

term_grammar = {
    "$START": ["$FACTOR"],
#    "$START": ["$EXPR"],
#    "$EXPR": ["$EXPR + $TERM", "$EXPR - $TERM", "$TERM"],
#    "$TERM": ["$TERM * $FACTOR", "$TERM / $FACTOR", "$FACTOR"],
#    "$FACTOR": ["+$FACTOR", "-$FACTOR", "($EXPR)", "$INTEGER", "$INTEGER.$INTEGER"],
    "$FACTOR": ["$INTEGER", "$INTEGER.$INTEGER"],
    "$INTEGER": ["$INTEGER$DIGIT", "$DIGIT"],
    "$DIGIT": ["0"] #, "1"] #, "2", "3", "4", "5", "6", "7", "8", "9"]
}

def is_symbol(x): return x[0] == '$'

class Line:
    __id = 0
    def __init__(self, rule, grammar, text, tfrom, parent):
        self.__dict__.update(locals())
        self.parts = self.rule
        self.at_part = 0
        self.myid = Line.__id
        Line.__id +=1

    def r(self): return len(self.text) - self.tfrom
    #def __eq__(self, o): return (self.rule == o.rule and self.tfrom == o.tfrom and self.text == o.text and self.parent == o.parent)
    def __str__(self): return "%d text: %s at: %s parts: %s"  % (self.myid, self.text, self.tfrom, str(self.parts))
    def __repr__(self): return str(self)
    def copy(self, tfrom): return Line(self.rule, self.grammar, self.text, tfrom, self.parent)

    def get_part(self):
        part = self.parts[self.at_part]
        self.at_part += 1
        return part

    def eof(self):
        return len(self.parts) <= self.at_part

    def explore(self):
        if self.eof():
            return []
        # take one step
        part = self.get_part()

        if not is_symbol(part):
            if self.text[self.tfrom:].startswith(part):
                if not self.parts:
                    # we matched. So let parent know
                    # from now, the parent will continue matching, but from the
                    # new tfrom. The parent has already dropped the
                    # corresponding part before creating us.
                    return [self.parent.copy(self.tfrom + len(part))]
                else:
                    # we need more steps to match. Return ourselves
                    self.tfrom = self.tfrom + len(part)
                    return [self]
            else:
                # failed to match a terminal. drop this line
                return []
        else:
            # each line will try to consume some of the input. Once it exhasusts
            # their on parts, and *some* input has been successfully consumed,
            # they will call the parent explore, but with an updated tfrom.
            return [Line(rule, self.grammar, self.text, self.tfrom, self) for rule in self.grammar[part]]

# Should return lines
def unify(key, grammar, text, tfrom=0, parent=None):
    rules = grammar[key]
    return [Line(rule, grammar, text, tfrom, parent) for rule in rules]

def using(fn):
    with fn as f: yield f

def processed(grammar):
    RE_NONTERMINAL = re.compile(r'(\$[a-zA-Z_]*)')
    new_grammar = {}
    for k, rules in grammar.items():
        new_grammar[k] = [[s for s in re.split(RE_NONTERMINAL, rule) if s] for rule in rules]
    return new_grammar

def parse(args, grammar):
    lines = unify('$START', processed(grammar), to_parse)
    while lines:
        #time.sleep(1)
        new_lines = []
        for l in sorted(lines, key=lambda x: x.r()):
            print(l)
            nl = l.explore()
            if nl:
                for l in nl:
                    if l.r() == 0:
                        return 'Matched'
                    # recursion.
                    if l not in new_lines:
                        new_lines.append(l)
            else:
                # unsuccessful. Drop this line
            #elif len(nl) == 1: success.
                pass
            pass
        print()
        lines = new_lines
    return None

if __name__ == '__main__':
    to_parse, = [f.read().strip() for f in using(open(sys.argv[1], 'r'))]
    grammar = term_grammar
    v = parse(to_parse, grammar)
    print()
    print(v)
