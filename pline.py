from lr1 import *
import logging as log
log.basicConfig( stream=sys.stdout, level=log.DEBUG )

class PLine:
    cache = {}
    counter = 0
    fdict = None
    def __init__(self, key, production, cursor=0, lookahead=set(), pnum=0):
        self.key,self.production,self.cursor,self.lookahead = key,production,cursor,lookahead
        self.tokens = split_production_str(self.production)
        self.pnum = pnum

    @classmethod
    def reset(cls):
        PLine.cache.clear()
        PLine.fdict = None
        PLine.counter = 0

    @classmethod
    def init_cache(cls, grammar, fdict):
        """
        Initializes the pline seeds
        >>> g = {}
        >>> g['$S'] = ['$E']
        >>> g['$E'] = ['$T + $E', '$T']
        >>> g['$T'] = ['1']
        >>> PLine.init_cache(g, follow(g, '$S', {}))
        4
        >>> et(str(PLine.cache[('$S', '$E', 0)]))
        '[p2]: $S -> $E  cursor: 0 @$'
        >>> et(str(PLine.cache[('$E', '$T + $E', 0)]))
        '[p0]: $E -> $T + $E  cursor: 0 @$'
        >>> et(str(PLine.cache[('$E', '$T', 0)]))
        '[p1]: $E -> $T  cursor: 0 @$'
        >>> et(str(PLine.cache[('$T', '1', 0)]))
        '[p3]: $T -> 1  cursor: 0 @ $+'
        >>> PLine.reset()
        """
        PLine.fdict = fdict
        for key in sorted(grammar.keys()):
            for production in grammar[key]:
                PLine.cache[(key, production, 0)] = PLine(key, production,
                        cursor=0, lookahead=fdict[key], pnum=PLine.counter)
                PLine.counter += 1
        return len(PLine.cache.keys())

    @classmethod
    def get(cls, key, production, cursor):
        """
        Try to get a predefined pline. If we fail, create new instead.
        """
        val = PLine.cache.get((key, production, cursor))
        if val: return val

        seed = PLine.cache.get((key, production, 0))
        val = PLine(key, production, cursor, seed.lookahead, seed.pnum)
        PLine.cache[(key, production, cursor)] = val

        return val

    @classmethod
    def from_seed(cls, obj, cursor):
        """
        To be used when we need a new pline when we advance the current pline.
        Important: the production rule is unchanged. Only the cursor may be
        different
        """
        return PLine.get(obj.key, obj.production, cursor)

    def production_number(self):
        """
        The number of the original production rule.
        Does not consider cursor location
        """
        return self.pnum

    def __repr__(self):
        return "[p%s]: %s -> %s \tcursor: %s %s" % (self.production_number(),
                self.key, ''.join([str(i) for i in self.tokens]), self.cursor, '@' + ''.join(sorted(self.lookahead)))

    def __str__(self):
        return "[p%s]: %s -> %s \tcursor: %s %s" % (self.production_number(),
                self.key, ''.join([str(i) for i in self.tokens]), self.cursor, '@' + ''.join(sorted(self.lookahead)))

    def advance(self):
        """
        creates a new pline with cursor incremented by one
        >>> PLine.reset()
        >>> g = {}
        >>> g['$S'] = ['$E']
        >>> g['$E'] = ['$T + $E', '$T']
        >>> g['$T'] = ['1']
        >>> PLine.init_cache(g, follow(g, '$S', {}))
        4
        >>> c = lr1_closure([PLine.get(key='$S', production='$E', cursor=0)], 0, g)
        >>> et(str(c[0]))
        '[p2]: $S -> $E  cursor: 0 @$'
        >>> et(str(c[0].advance()))
        "('$E', [p2]: $S -> $E  cursor: 1 @$)"
        >>> et(str(c[1]))
        '[p0]: $E -> $T + $E  cursor: 0 @$'
        >>> et(str(c[1].advance()))
        "('$T', [p0]: $E -> $T + $E  cursor: 1 @$)"
        >>> et(str(c[2]))
        '[p1]: $E -> $T  cursor: 0 @$'
        >>> et(str(c[2].advance()))
        "('$T', [p1]: $E -> $T  cursor: 1 @$)"
        >>> PLine.reset()
        """

        if self.cursor >= len(self.tokens):
            return '', None
        token = self.at(self.cursor)
        return token, PLine.from_seed(self, self.cursor+1)
    def at(self, cursor):
        if cursor >= len(self.tokens): return None
        return self.tokens[cursor]

def lr1_closure(closure, cursor, grammar):
    """
    >>> g = {}
    >>> g['$S'] = ['$E']
    >>> g['$E'] = ['$T + $E', '$T']
    >>> g['$T'] = ['1']
    >>> PLine.init_cache(g, follow(g, '$S', {}))
    4
    >>> c = lr1_closure([PLine.get(key='$S', production='$E', cursor=0)], 0, g)
    >>> c = [et(str(l)) for l in c]
    >>> len(c)
    4

    TODO: verify if $ belongs here.

    >>> c[0]
    '[p2]: $S -> $E  cursor: 0 @$'
    >>> c[1]
    '[p0]: $E -> $T + $E  cursor: 0 @$'
    >>> c[2]
    '[p1]: $E -> $T  cursor: 0 @$'
    >>> c[3]
    '[p3]: $T -> 1  cursor: 0 @ $+'
    >>> PLine.reset()
    """
    # get non-terminals following start.cursor
    # a) Add the item itself to the closure
    items = closure[:] # copy
    seen = set()
    #for i in items: seen.add(i.key)
    # c) Repeat (b, c) for any new items added under (b).
    while items:
        item, *items = items
        # b) For any item in the closure, A :- α . β γ where the next symbol
        # after the dot is a nonterminal, add the production rules of that
        # symbol where the dot is before the first item
        # (e.g., for each rule β :- γ, add items: β :- . γ
        token = item.at(item.cursor)
        if not token: continue
        if token in seen: continue
        if is_nonterminal(token):
            for ps in grammar[token]:
                pl = PLine.get(key=token, production=ps, cursor=0)
                items.append(pl)
                closure.append(pl)
                seen.add(pl.key)
    return closure

