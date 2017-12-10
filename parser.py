#!/usr/bin/env python3
import sys
import time
import re
import collections

term_grammar = {
    "$START": ["$FACTOR"],
    "$EXPR": ["$EXPR + $TERM", "$EXPR - $TERM", "$TERM"],
    "$TERM": ["$TERM * $FACTOR", "$TERM / $FACTOR", "$FACTOR"],
    "$FACTOR": ["$INTEGER", "$INTEGER.$INTEGER"],
    "$INTEGER": ["$INTEGER$DIGIT", "$DIGIT"],
    "$DIGIT": ["0", "1"] #, "2", "3", "4", "5", "6", "7", "8", "9"]
}

def is_symbol(x): return x[0] == '$'

def log(v=None):
    if v: print(v, file=sys.stderr, flush=True)
    else: print(file=sys.stderr, flush=True)

class Line:
    NoMatch = 0
    Matched = 1
    PartMatch = 2
    RuleMatch = 3
    Explore = 4

    __id = 0
    register = {}

    def __init__(self, rule, grammar, text, tfrom, parent):
        self.__dict__.update(locals())
        self.parts = self.rule
        self.at_part = 0
        self.myid = Line.__id
        Line.__id +=1
        Line.register[self.myid] = self
        self._key = "[rule:%s from:%d]" % (str(self.rule), self.tfrom)

    def key(self):
        return self._key

    def text_remaining(self):
        return len(self.text) - self.tfrom - 1

    def __str__(self):
        return "%d:%s (%s)" %(self.myid, self.key(), self.text[self.tfrom:])
        #return ("{%d| rule:%s text:%s from:%d parts:%s: at_part:%d}"  %
        #        (self.myid, str(self.rule), self.text[self.tfrom:], self.tfrom,
        #         str(self.parts[self.at_part:]), self.at_part))
    def __repr__(self): return str(self)
    def copy_on_match(self, tfrom):
        #log("Retrive[%d] %s:" % (self.myid, self.rule))
        l = Line(self.rule, self.grammar, self.text, tfrom, self.parent)
        l.myid = self.myid
        l.key = self.key
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
                    return (Line.Matched, [])
                else: # False match
                    return (Line.NoMatch, [])

            # we matched. So let parent know
            # from now, the parent will continue matching, but from the
            # new tfrom. The parent has already dropped the
            # corresponding part before creating us.
            return (Line.RuleMatch, [self.parent.copy_on_match(self.tfrom)])

        # take one step
        part = self.get_part()
        if not is_symbol(part):
            if self.text[self.tfrom:].startswith(part):
                self.tfrom += len(part)
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
    return [Line(rule, grammar, text, tfrom, parent) for rule in grammar[key]]

def add_to_rules(my_line, my_lines, my_rules, my_sleepers):
    l_key = my_line.key()
    if l_key in my_rules:
        # if a similar rule is under consideration, add ourselves to
        # sleepers.
        if l_key in my_sleepers:
            my_sleepers[l_key].add(my_line)
        else:
            my_sleepers[l_key] = set([my_line])
    else:
        my_lines.append(my_line)
        my_rules.add(l_key)

def wake_up_cosleepers(line, lines, current_rules, sleepers):
    if line.key() not in sleepers:
        return
    my_sleepers = sleepers[line.key()]
    del sleepers[line.key()]
    for co_sleeper in my_sleepers:
        log("waking %s: %d" % (line.key(), co_sleeper.myid))
        l = co_sleeper.parent.copy_on_match(line.tfrom)
        log("%d: %d > %s" % (line.myid, co_sleeper.myid, l))
        add_to_rules(l, lines, current_rules, sleepers)
        wake_up_cosleepers(co_sleeper, lines, current_rules, sleepers)

def parse(args, grammar):
    lines = unify('$START', processed(grammar), to_parse)
    sleepers = {}
    current_rules = set([l.key() for l in lines])
    register_children = {}
    answers = {}
    while lines:
        line, *lines = lines
        line_key = line.key()
        current_rules.remove(line_key)
        log(line)
        match, children = line.explore()
        if match == Line.Matched:
            log("matched")
            return

        elif match == Line.PartMatch:
            # nothing to do. Just another step.
            assert len(children) == 1
            _line = children[0]
            log("partmatch.")
            add_to_rules(_line, lines, current_rules, sleepers)

        elif match == Line.RuleMatch:
            answers[line.key()] = line.tfrom
            # wake the sleepers, and add their parents because the
            # cosleepers matched.
            wake_up_cosleepers(line, lines, current_rules, sleepers)

            assert len(children) == 1
            _line = children[0]
            add_to_rules(_line, lines, current_rules, sleepers)

        elif match == Line.Explore:
            if line_key not in register_children:
                register_children[line_key] = len(children)
            for l in children:
                l_key = l.key()
                if l_key in answers:
                    # if we already know the answer, dont bother.
                    if answers[l.key()] != -1:
                        log("had_an_answer for %s" % l.key())
                        ln = line.parent.copy_on_match(answers[l_key])
                        log(".%s" % ln)
                        wake_up_cosleepers(ln, lines, current_rules, sleepers)
                        add_to_rules(ln, lines, current_rules, sleepers)
                    else:
                        # no match
                        if l_key in sleepers:
                            del sleepers[l_key]
                        log("\t\tcX %s" % l)
                else:
                    log("> %s" % l)
                    add_to_rules(l, lines, current_rules, sleepers)

        elif match == Line.NoMatch:
            # we need to be careful here. We can do this only if we
            # know that all children of line, and their children failed to
            # match.
            if line_key in register_children:
                register_children[line_key] -= 1
                if register_children[line_key] == 0:
                    answers[line.key()] = -1
            else:
                answers[line.key()] = -1
            # and drop the sleepers
            if line_key in sleepers:
                del sleepers[line_key]
            log("\t\tX %s" % line)

        log()
    return None

def using(fn):
    with fn as f: yield f

def processed(grammar):
    RE_NONTERMINAL = re.compile(r'(\$[a-zA-Z_]*)')
    new_grammar = {}
    for k, rules in grammar.items():
        new_grammar[k] = [[s for s in re.split(RE_NONTERMINAL, rule) if s] for rule in rules]
    return new_grammar


if __name__ == '__main__':
    to_parse, = [f.read().strip() for f in using(open(sys.argv[1], 'r'))]
    grammar = term_grammar
    v = parse(to_parse, grammar)
    log()
    log(v)
