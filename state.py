from pline import *
class State:
    counter = 1
    registry = {}
    cache = {}
    def reset():
        PLine.reset()
        State.counter = 1
        State.registry = {}
        State.cache = {}

    def __init__(self, plines, sfrom=None):
        self.plines = plines
        self.shifts = {}
        self.go_tos = {}
        self.i = State.counter
        self.row = []
        self.note = "*"
        if sfrom:
            self.grammar = sfrom.grammar
            self.start = sfrom.start
        State.counter += 1
        State.registry[self.i] = self
        self.key = ''.join([str(l) for l in plines])
        if State.cache.get(self.key): raise Exception("Cache already has the state. Use State.get")
        State.cache[self.key] = self

    @classmethod
    def get(cls, plines, sfrom=None):
        key = ''.join([str(l) for l in plines])
        val = State.cache.get(key)
        if val: return val
        State.cache[key] = State(plines, sfrom)
        return State.cache[key]



    def __str__(self):
        return "State(%s):\n\t%s" % (self.i, "\n\t".join([str(i) for i in self.plines]))

    def __repr__(self): return str(self)

    @classmethod
    def construct_initial_state(cls, grammar, start='$START'):
        """
        >>> State.reset()
        >>> g = {}
        >>> g['$S'] = ['$E']
        >>> g['$E'] = ['$T + $E', '$T']
        >>> g['$T'] = ['1']
        >>> s = State.construct_initial_state(g, start='$S')
        >>> l = [et(str(l)) for l in s.plines]
        >>> len(l)
        4
        >>> l[0]
        '[p2]: $S -> $E.$  cursor: 0 @$'
        >>> l[1]
        '[p0]: $E -> $T + $E  cursor: 0 @$'
        >>> l[2]
        '[p1]: $E -> $T  cursor: 0 @$'
        >>> l[3]
        '[p3]: $T -> 1  cursor: 0 @ $+'
        >>> State.reset()
        """
        PLine.init_cache(grammar, follow(grammar, start, {}))
        key = start
        production_str = grammar[key][0]

        pl = PLine.get(key=key, production=production_str, cursor=0)
        pl.tokens.append(Dollar())

        lr1_items = lr1_closure(closure=[pl], cursor=0, grammar=grammar)
        state =  cls(lr1_items, 0)
        # seed state
        state.start, state.grammar = start, grammar
        return state

    def go_to(self, token):
        """
        >>> State.reset()
        >>> g = {}
        >>> g['$S'] = ['$E']
        >>> g['$E'] = ['$T + $E', '$T']
        >>> g['$T'] = ['1']
        >>> s = State.construct_initial_state(g, start='$S')
        >>> et(str(s.go_to('$T')))
        'State(1 -> [$T] ->  2):  [p0]: $E -> $T + $E  cursor: 1 @$  [p1]: $E -> $T  cursor: 1 @$'
        >>> et(str(s.go_to('1')))
        'None'
        >>> State.reset()
        """
        if self.go_tos.get(token): return self.go_tos[token]
        if is_terminal(token): return None
        new_plines = []
        for pline in self.plines:
            tadv, new_pline = pline.advance()
            if token == tadv:
                new_plines.append(new_pline)
        if not new_plines: return None
        s = State.get(plines=new_plines, sfrom=self)
        self.go_tos[token] = s
        s.note = "%s -> [%s] -> " % (self.i,  token)
        return s

    def shift_to(self, token):
        """
        >>> State.reset()
        >>> g = {}
        >>> g['$S'] = ['$E']
        >>> g['$E'] = ['$T + $E', '$T']
        >>> g['$T'] = ['1']
        >>> s = State.construct_initial_state(g, start='$S')
        >>> et(str(s.shift_to('$T')))
        'None'
        >>> et(str(s.shift_to('1')))
        'State(1 -> [1] ->  2):  [p3]: $T -> 1  cursor: 1 @ $+'
        >>> State.reset()
        """
        if self.shifts.get(token): return self.shifts[token]
        if is_nonterminal(token): return None
        new_plines = []
        for pline in self.plines:
            tadv, new_pline = pline.advance()
            if token == tadv:
                new_plines.append(new_pline)
        if not new_plines: return None
        # each time we shift, we have to build a new closure, with cursor at 0
        # for the newly added rules.
        s = self.form_closure(new_plines)
        self.shifts[token] = s
        s.note = "%s -> [%s] -> " % (self.i,  token)
        return s

    def form_closure(self, plines):
        closure = lr1_closure(closure=plines, cursor=0, grammar=self.grammar)
        s = State.get(plines=plines, sfrom=self)
        return s

    def accept(self):
        for pline in self.plines:
            if pline.at(pline.cursor) == Dollar():
                return True
        return False

    def can_reduce(self, nxt_tok):
        # is the cursor at the end in any of the plines?
        for pline in self.plines:
            if pline.cursor + 1 >= len(pline.tokens):
                res = nxt_tok in pline.lookahead
                if res: return pline
        # return the production number too for this pline
        return None


    @classmethod
    def construct_states(cls, grammar, start='$START'):
        """
        >>> State.reset()
        >>> g = {}
        >>> g['$S'] = ['$E']
        >>> g['$E'] = ['$T', '$T + $E']
        >>> g['$T'] = ['1']
        >>> s = State.construct_states(g, '$S')
        >>> len(State.registry)
        6

        >> len(s.shifts) # there should be two shifts
        2
        >> len(s.go_tos) # there should be 4 gotos
        4

        >>> et(str(s.shift_to('$T')))
        'None'
        >>> et(str(s.go_to('$T')))
        'State(5 -> [$T] ->  3):  [p0]: $E -> $T  cursor: 1 @$  [p1]: $E -> $T + $E  cursor: 1 @$'
        >>> et(str(s.go_to('$E')))
        'State(1 -> [$E] ->  2):  [p2]: $S -> $E  cursor: 1 @$'
        >>> len(State.registry) # todo -- two of them -- state3, and state4 are dups
        6
        >>> State.reset()
        """

        state1 = State.construct_initial_state(grammar, start)
        states = [state1]
        follow = {}
        all_states = []
        seen = set()
        while states:
            state, *states = states
            all_states.append(state)
            for key in sorted(symbols(grammar)): # needs terminal symbols too.
                if is_terminal(key):
                    new_state = state.shift_to(key)
                    if new_state and new_state.key not in seen:
                        states.append(new_state)
                        seen.add(new_state.key)
                        state.row.append((key,'Shift', new_state.i))
                    else:
                        state.row.append((key,'_', None))
                else:
                    new_state = state.go_to(key)
                    if new_state and new_state.key not in seen:
                        states.append(new_state)
                        seen.add(new_state.key)
                        state.row.append((key,'Goto', new_state.i))
                    else:
                        state.row.append((key,'_', None))
        for state in all_states:
            # for each item, with an LR left of Dollar, add an accept.
            # for each item, with an LR with dot at the end, add a reduce
            # r p
            for line in state.plines:
                if line.at(line.cursor) == Dollar():
                    key = '$'
                    state.row.append((key, 'Accept', None))
                elif line.cursor + 1 > len(line.tokens):
                    for key in line.lookahead:
                        state.row.append((key, 'Reduce', line.key))
        return state1

if __name__ == '__main__':
  State.reset()
  g = {}
  g['$S'] = ['$E']
  g['$E'] = ['$T+$E', '$T']
  g['$T'] = ['1']
  s = State.construct_states(g, start='$S')
  for k,s in State.registry.items():
      print(k, s.row)
  State.reset()
