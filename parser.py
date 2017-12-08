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

def log(v=None):
    if v:
        print(v, file=sys.stderr, flush=True)
    else:
        print(file=sys.stderr, flush=True)

class ParseCache:
    def __init__(self):
        self.__dict__.update(locals())
        self.members = {}
        self.first = {}

    def add_lines(self, lines):
        for l in lines:
            if l.key() in self.members:
                self.members[l.key()].append(l)
            else:
                self.members[l.key()] = [l]
                self.first[l.key()] = l # get only the first

    def shift_up(self):
        members = self.members
        self.first = {}
        self.members = {}
        for k,v in members.items():
            _current, *rest = v
            if rest:
                self.members[k] = rest
                self.first[k] = rest[0]

    def firsts(self):
        return self.first.values()

    def pop_firsts(self):
        self.shift_up()

    def has_remaining(self):
        return len(self.members) > 0

    def get_cosleepers(self, orig_key, tfrom):
        co_parsed = self.members[orig_key]
        # each sleeper will have different parents, otherwise they
        # are all same. We use the current from, becaue the line was matched
        # just now.
        # use the tfrom of the current line because it contains the
        # length of part matched.
        return [x.parent.copy_on_match(tfrom) for x in co_parsed]

class Line:
    NoMatch = 0
    Matched = 1
    PartMatch = 2
    Explore = 3

    __id = 0
    parse_cache = {}
    def __init__(self, rule, grammar, text, tfrom, parent):
        self.__dict__.update(locals())
        self.parts = self.rule
        self.at_part = 0
        self.myid = Line.__id
        Line.__id +=1

    def xkey(self, tfrom, at_part):
        return ("[key| %s %d part:%d]" % (str(self.rule), tfrom, at_part))

    def key(self):
        return self.xkey(self.tfrom, self.at_part)

    def text_remaining(self): return len(self.text) - self.tfrom - 1
    #def __eq__(self, o): return (self.rule == o.rule and self.tfrom == o.tfrom and self.text == o.text and self.parent == o.parent)
    def __str__(self): return "{%d text: %s at: %s parts: %s:%d}"  % (self.myid, self.text, self.tfrom, str(self.parts), self.at_part)
    def __repr__(self): return str(self)
    def copy_on_match(self, tfrom):
        l = Line(self.rule, self.grammar, self.text, tfrom, self.parent)
        l.at_part = self.at_part + 1
        return l

    def get_part(self):
        part = self.parts[self.at_part]
        self.at_part += 1
        return part

    def text_eof(self):
        return len(self.text) <= self.tfrom

    def part_eof(self):
        return len(self.parts) <= self.at_part

    def explore(self):
        if self.part_eof():
            # we were inserted back into the queue by a matched child
            if not self.parent:
                # have we exhausted the text?
                if self.text_eof():
                    assert False
                    return (Line.Matched, [])
                    return True
                else: # False match
                    return (Line.NoMatch, [])
            return (Line.Matched, [self.parent.copy_on_match(self.tfrom)])
        # take one step
        part = self.get_part()

        if not is_symbol(part):
            if self.text[self.tfrom:].startswith(part):
                if self.part_eof():
                    # we matched. So let parent know
                    # from now, the parent will continue matching, but from the
                    # new tfrom. The parent has already dropped the
                    # corresponding part before creating us.
                    self.tfrom += len(part)
                    return (Line.Matched, [self.parent.copy_on_match(self.tfrom)])
                else:
                    # we need more steps to match. Return ourselves
                    self.tfrom = self.tfrom + len(part)
                    return (Line.PartMatch, [self])
            else:
                # failed to match a terminal. drop this line
                return (Line.NoMatch, [])
        else:
            # each line will try to consume some of the input. Once it exhasusts
            # their on parts, and *some* input has been successfully consumed,
            # they will call the parent explore, but with an updated tfrom.
            return (Line.Explore, [Line(rule, self.grammar, self.text, self.tfrom, self) for rule in self.grammar[part]])

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
    p = ParseCache()
    p.add_lines(unify('$START', processed(grammar), to_parse))
    while p.has_remaining():
        new_lines = []
        uniq_rules = p.firsts()
        for line in uniq_rules:
            log(line)
            orig_key = line.key()
            match, children = line.explore()
            if match == Line.NoMatch:
                # drop from parse_cache if this was unsuccessful.
                log("\t\tX %s" % line)
            elif match in [Line.Explore, Line.PartMatch, Line.Matched]:
                if  match == Line.Matched:
                    # line key gets modified after line.explore. So use the last key pos
                    sleepers = p.get_cosleepers(orig_key, line.tfrom)
                    new_lines.extend(sleepers)
                    # successful, get the co-parsed from parse cache, and updte them
                    # all to new_lines
                for l in children:
                    log("> %s" % l)
                    if l.text_remaining() == 0:
                        return 'Matched'
                    # recursion.
                    new_lines.append(l)
            pass
        log()
        p.pop_firsts()
        p.add_lines(new_lines)
    return None

if __name__ == '__main__':
    to_parse, = [f.read().strip() for f in using(open(sys.argv[1], 'r'))]
    grammar = term_grammar
    v = parse(to_parse, grammar)
    log()
    log(v)
