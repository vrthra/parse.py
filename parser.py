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
        self.seen = {}

    def add_lines(self, lines):
        for l in lines:
            if l.key() in self.members:
                self.members[l.key()].append(l)
            else:
                self.members[l.key()] = [] # first one goes to first
                self.first[l.key()] = l # get only the first

    def shift_up(self):
        members = self.members
        self.first = {}
        self.members = {}
        for k,v in members.items():
            if not v: continue
            _current, *rest = v
            if rest:
                self.members[k] = rest[1:]
                self.first[k] = rest[0]

    def firsts(self):
        return self.first.values()

    def drop(self, key):
        self.seen[key] = -1
        del self.members[key]

    def pop_firsts(self):
        self.shift_up()

    def has_remaining(self):
        return len(self.members) > 0

    def has_key(self, key):
        return key in self.seen

    def get_matched(self, line):
        if self.seen[line.key()] == -1: return None
        log("Cached:")
        return line.parent.copy_on_match(self.seen[line.key()])

    def get_cosleepers(self, orig_key, tfrom):
        # register ourselves so that any future call gets treated the same 
        # way with tfrom and at
        self.seen[orig_key] = tfrom

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

    def key(self):
        return ("[rule:%s from:%d part:%d]" %
                (str(self.rule), self.tfrom, self.at_part))

    def text_remaining(self):
        return len(self.text) - self.tfrom - 1

    def __str__(self):
        return ("{%d| rule:%s text:%s from:%d parts:%s: at_part:%d}"  %
                (self.myid, str(self.rule), self.text[self.tfrom:], self.tfrom, str(self.parts[self.at_part:]), self.at_part))
    def __repr__(self): return str(self)
    def copy_on_match(self, tfrom):
        log("Retrive[%d] %s:" % (self.myid, self.rule))
        l = Line(self.rule, self.grammar, self.text, tfrom, self.parent)
        l.myid = self.myid
        # Unlike tfrom we dont have to increment at_part because it would
        # already have been incremented when the parent started exploring this
        # nt
        l.at_part = self.at_part
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
                else: # False match
                    return (Line.NoMatch, [])

            # we matched. So let parent know
            # from now, the parent will continue matching, but from the
            # new tfrom. The parent has already dropped the
            # corresponding part before creating us.
            return (Line.Matched, [self.parent.copy_on_match(self.tfrom)])

        # take one step
        part = self.get_part()
        if not is_symbol(part):
            if self.text[self.tfrom:].startswith(part):
                self.tfrom += len(part)
                return (Line.Matched, [self])
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
        for line in sorted(uniq_rules, key=lambda x: x.text_remaining()):
            log(line)
            if p.has_key(line.key()):
                # no need to explore. Just match, and add ourparent to
                # the new_lines
                parent = p.get_matched(line)
                if parent:
                    new_lines.append(parent)
            else:
                orig_key = line.key()
                match, children = line.explore()
                if match == Line.NoMatch:
                    # drop from parse_cache if this was unsuccessful.
                    # TODO: we also want to drop and mark the path this
                    # particular match took. I.e. all the children and
                    # grand children
                    p.drop(orig_key)
                    log("\t\tX %s" % line)
                elif match in [Line.Explore, Line.PartMatch, Line.Matched]:
                    if  match == Line.Matched:
                        # line key gets modified after line.explore. So use the last key pos
                        sleepers = p.get_cosleepers(orig_key, line.tfrom)

                        # we need to update the at_part because cosleepers
                        # went to sleep before match
                        for i in sleepers:
                            i.at_part += 1
                            log("s> %s" % i)
                        new_lines.extend(sleepers)
                        # successful, get the co-parsed from parse cache, and updte them
                        # all to new_lines
                    for l in children:
                        log("> %s" % l)
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
