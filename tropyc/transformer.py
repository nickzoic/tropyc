
# XXX modify this so that each instruction gets its own object and stack frame: as we go around a loop 
# the stack frames should hopefully line up.

import sys
import disx
import pprint
import re

# XXX What would be nice is instead of keeping a stack of string expressions,
# which is bit clumsy, we could keep a stack of objects thus getting some 
# type information along for the ride.   This would also help with precedence.

class State:
    """Holds the state of the virtual machine at a given instant,
    which is the instruction pointer and the expression stack.
    Provides simple stack operations used by the OpCodes."""
    
    def __init__(self, copyfrom=None, offset=None):
        self.offset = offset if offset is not None else copyfrom.offset if copyfrom else 0
        self.stack = copyfrom.stack[:] if copyfrom else []

    def push(self, arg):
        self.stack.insert(0, arg)

    def pop(self):
        return self.stack.pop(0)

    def pop2(self):
        a = self.stack.pop(0)
        b = self.stack.pop(0)
        return b,a

    def popn(self, n):
        ll = self.stack[0:n]
        self.stack[0:n] = []
        return ll

    def peek(self):
        return self.stack[0]

    def peekn(self, n):
        return self.stack[0:n]
    
    def peekx(self, n):
        return self.stack[n]
    
    def rot(self, n=1):
        self.stack[0:n] = self.stack[n-1::-1]

    def dup(self, n=1):
        self.stack[0:0] = self.stack[0:n]

    def is_empty(self):
        return len(self.stack) == 0



# Translate Opcode names to Javascript operators.
# XXX It would be really nice to add in a more intelligent
# expression generator, so we don't get such
# a parentheses salad here, and so we're not hacking on 
# strings all the time.  Also, typing could allow us to tell
# the difference between string format and modulo eg:
# `"foo%sbar" % 7` and `127 % 7` at least some of the time.

UnaryOperatorFormats = {
    'positive': '(+{0})',
    'negative': '(-{0})',
    'not':      '(!{0})',
    'convert':  'repr({0})',  # XXX not actually supported (yet)
}

# XXX BINARY_MODULO is also used for string formatting,
# so we're going to have to turn that into a function call.
# although it might also be possible to keep track of types 
# in the expression stack and avoid this somethings.

BinaryOperatorFormats = {
    'power':        'Math.pow({0},{1})',
    'multiply':     '({0}*{1})',
    'divide':       'Math.floor({0}/{1})',
    'floor_divide': 'Math.floor({0}/{1})',
    'true_divide':  '({0}/{1})',
    'modulo':       '({0}%{1})',
    'add':          '({0}+{1})',
    'subtract':     '({0}-{1})',
    'subscr':       '({0}[{1}])',
    'lshift':       '({0}<<{1})',
    'rshift':       '({0}>>{1})',
    'and':          '({0}&{1})',
    'xor':          '({0}^{1})',
    'or':           '({0}|{1})',
}

CompareOperatorFormats = {
    '<':      '({0}<{1})',
    '<=':     '({0}<={1})',
    '==':     '({0}=={1})',
    '>=':     '({0}>={1})',
    '>':      '({0}>{1})',
    '!=':     '({0}!={1})',
    'in':     '({0} in {1})',
    'not in': '!({0} in {1})',
    'is':     '({0} === {1})',
    'is not': '({0} !== {1})',
}
    
    
class CodeOp:
    
    """Container for the opcode, including logic to evaluate its effects on the stack."""

    def __init__(self, codefunc, offset, op_name, value):
        """Just initialize the object, don't really do anything yet."""
        
        self.codefunc = codefunc
        self.offset = offset
        self.op_name = op_name
        self.value = value
        
        # XXX codea is used for loop instructions, codeb for normal ones.
        # this is a bit of an artefact of the way code is generated and 
        # should be cleaned up.
        self.codea = ""
        self.codeb = ""
        
        self.visited = False
    
    def execute(self, oldstate):
        """Run this op, making up some new states."""
        
        state = State(oldstate, self.offset + (3 if self.value is not None else 1))
        
        # PURE FUNCTIONAL STUFF
        
        self.visited = True
        
        if self.op_name == 'NOP': pass

        elif self.op_name in ('LOAD_CONST', 'LOAD_NAME', 'LOAD_FAST', 'LOAD_GLOBAL'):
            state.push(self.value)
        elif self.op_name == 'LOAD_ATTR':
            state.push("%s.%s" % (self.extra, state.pop()))
        
        elif self.op_name.startswith('UNARY_'):
            operator = lc(self.op_name[self.op_name.find("_")+1:])                        
            state.push(UnaryOperatorFormats[operator].format(state.pop()))
        
        elif self.op_name.startswith('BINARY_') or self.op_name.startswith('INPLACE_'):
            operator = self.op_name[self.op_name.find("_")+1:].lower()
            state.push(BinaryOperatorFormats[operator].format(*state.pop2()))
        
        elif self.op_name == 'COMPARE_OP':
            tos, tos1 = state.pop2()
            state.push(CompareOperatorFormats[self.value].format(tos, tos1))
        
        elif self.op_name == 'POP_TOP':   state.pop()
        
        # XXX It would be nice to know if top-of-stack was already
        # a variable rather than a constant expression so we don't have
        # to assign it to one to copy it!
        
        elif self.op_name == 'DUP_TOP':
            top = state.peek()
            if top.startswith(self.codefunc.prefix):
                # This is a variable already, don't reassign it.
                state.push(top)
            else:
                tos = state.pop()
                temp = self.codefunc.templabel()
                self.codeb = "var %s = %s;" % (temp, tos)
                state.push(temp)
                state.push(temp)
            
        elif self.op_name == 'DUP_TOPX':
            # This probably needs to be optimized, it is pretty awful.
            tosn = state.popn(self.value)
            temps = []
            for val in tosn:
                temp = self.codefunc.templabel()
                self.codeb += "var %s = %s;" % (temp, val)
                temps.append(temp)
            for temp in temps:
                self.stack.push(temp)
            for temp in temps:
                self.stack.push(temp)
                
        elif self.op_name == 'ROT_TWO':   state.rot(2)
        elif self.op_name == 'ROT_THREE': state.rot(3)
        elif self.op_name == 'ROT_FOUR':  state.rot(4)
        
        elif self.op_name == 'SLICE+0':   state.push("%s.slice()" % state.pop())
        elif self.op_name == 'SLICE+1':   state.push("%s.slice(%s)" % state.pop2())
        elif self.op_name == 'SLICE+2':   state.push("%s.slice(0,%s)" % state.pop2())
        elif self.op_name == 'SLICE+3':   state.push("%s.slice(%s,%s)" % state.popn(3))

        elif self.op_name in ('BUILD_LIST', 'BUILD_TUPLE'): 
            ll = reversed(state.popn(self.value))
            temp = self.codefunc.templabel()
            self.codeb = ("var %s = [" % temp) + (",".join(x for x in ll)) + "];"
            state.push(temp)
        
        elif self.op_name == 'BUILD_MAP': state.push("{}")

        elif self.op_name in ('STORE_NAME', 'STORE_FAST'): self.codeb = "%s = %s;" % (self.value, state.pop())
        elif self.op_name == 'STORE_MAP':
            k, v, m = state.popn(3)
            if m == '{}':
                state.push("{%s:%s}" % (k,v))
            elif m.endswith("}"):
                state.push(m[:-1] + ",%s:%s" % (k,v) + "}")
            else:
                raise NotImplementedError("Trying to STORE_MAP to something not a hash?")

        elif self.op_name == 'STORE_ATTR':
            val, obj = state.pop2()
            self.codeb = "%s.%s = %s" % (obj, self.value, val)

        elif self.op_name == 'UNPACK_SEQUENCE':
            tos = state.pop()
            for n in range(0, self.value):
                # XXX Do we need to use temp values like DUP_TOP does?            
                #temp = temp_var(n)
                #self.code += "var %s = %s[%d];" % (temp, tos, n)
                #state.push(temp)
                state.push("%s[%d]" % (tos, n))
        
        # XXX it is a really minor one, but wouldn't it be nice to 
        # gather all the PRINT_ITEMs together into a print items buffer
        # or something.
        
        elif self.op_name == 'PRINT_ITEM': self.codeb = "print(%s);" % state.pop()
        elif self.op_name == 'PRINT_NEWLINE': self.codeb = "print('-----');"
        
        elif self.op_name == 'LIST_APPEND':
            self.codeb = "%s.push(%s);" % (state.peekx(self.value or 1), state.pop())
        
        elif self.op_name in ('DELETE_NAME', 'DELETE_FAST'):
            self.codeb = "delete %s;" % self.value
        
        elif self.op_name == 'DELETE_ATTR': self.codeb = "delete %s.%s;" % (self.value, state.pop())
        
        elif self.op_name == 'RETURN_VALUE':
            self.codeb = "return %s;" % state.pop()
            if not state.is_empty():
                raise NotImplementedError(">>> RETURN_VALUE STACK %s" % repr(state.stack))
            return []
        
        elif self.op_name == 'CALL_FUNCTION':
            # XXX we don't handle kwargs yet ... need to work out how 
            # to call kwargish functions using `options` or whatever.
            kwargs = state.popn(int(self.value / 256) * 2)      
            args = reversed(state.popn(self.value % 256))
            func = state.pop()
            
            # Functions are always saved rather than added to 
            # the expression state because that way we know they'll
            # actually get run right away.
            
            # XXX it would be nice to optimize away void functions
            # (followed by POP_TOP) or functions immediately followed
            # by a STORE.  This could be done by pushing a function
            # expression onto the stack, and "freezing" that if the
            # next instruction isn't a POP_TOP or STORE or RETURN_VALUE
            # or PRINT_ITEM or whatever.
            
            temp = self.codefunc.templabel()
            self.codeb = "var %s = %s(%s);" % (temp, func, ",".join(args))
            state.push(temp)
        
        #elif self.op_name == 'RAISE_VARARGS':
        #    ll = state.popn(self.value)
        #    self.codeb = "raise (%s);" % ",".join(ll)
        
        # LOOPING AND BRANCHING
        
        # XXX javascript looping construct most likely is probably 
        # while(1) { if (exitcondition) break; if (loopcondition) continue; break; }
        # but I have to identify the loops somehow.
        
        # XXX The current state of things is a bit kludgey: I'm going to leave it like this for now,
        # but here's an alternative loop finder:
        #
        # 1. Find all backwards jumps.  These can only be implemented as continues of loops
        # 2. For each backwards jump target, introduce the start of a loop.
        # 3. Find the last backwards jump for each backwards jump target.  If it is a conditional,
        #    code it as a "if (!condition) break loopname;", otherwise it needs no code (and the loop will continue)
        # 4. All other backwards jumps become "if (condition) continue loopname;".
        # 5. Find all forwards jumps that go out of the loop.  If they are right at the start of the loop, they can
        #    become the "while" condition.  Otherwise they are "if (condition) break loopname;".
        # 6. Any gap between the last conditional continue and the target of the breaks must be a for/else clause.
        #    this isn't part of Javascript but can be modelled with:
        #        loop1: do { while (loop_condition) { if (break_condition) break loop1; loop_action; } else_action; } while(0);
        #    some things might only break loop2 though
        # 7. All other jumps must be if/elif/else trees.  If they cross loop boundaries, vomit.
        
        # XXX at the moment, for/else isn't handled at all.
        
        elif self.op_name == 'SETUP_LOOP':
            self.jumpoffs = self.value
            label = self.codefunc.block_add(self.offset, self.value)
            self.codea = "%s: while (1) {" % label
            self.codefunc.codeops[self.value].codea = "break %s; }" % label
        
        elif self.op_name == 'GET_ITER':
            # XXX This should push a closure instead of just making
            # another reference to the list.  On the other hand, I suppose
            # it is much the same thing so maybe it should just "pass"
            pass
            #iterable = state.pop()
            #temp = self.codefunc.templabel()
            #self.codeb = "var %s = %s;" % (temp, iterable)
            #state.push(temp)
        
        elif self.op_name == 'FOR_ITER':
            # We actually leave the pointless outer loop in place, just so
            # BREAK_LOOP has somewhere to go to and we can support for/else
            # therefore.
            self.jumpoffs = self.value
            label = self.codefunc.block_add(self.offset, self.value, is_iter=True)
            iterator = state.peek()
            temp = self.codefunc.templabel()
            self.codea = "%s: for (var %s in %s) {" % (label, temp, iterator)
            self.codefunc.codeops[self.value].codea = "break %s; }" % label
            state.push("%s[%s]" % (iterator, temp))
            
            endstate = State(oldstate, self.value)
            endstate.pop()
            return [state, endstate]
        
        elif self.op_name == 'POP_BLOCK':
            # We don't actually need to do anything here because 
            # block_inner searches for the appropriate block anyway.
            # XXX doing this the obvious way would probably be more efficient.
            pass
        
        elif self.op_name == 'CONTINUE_LOOP':
            label, start = state.block_start(self.value - 3)
            self.codeb = "continue %s;" % label
            state.offset = start
            
        elif self.op_name == 'BREAK_LOOP':
            label, start, end = self.codefunc.block_inner(self.offset, find_iter=False)
            self.codeb = "break %s;" % label
            state.offset = end
        
        elif self.op_name.startswith("JUMP_") or self.op_name.startswith("POP_JUMP_"):
            # XXX don't forget JUMP_IF_{TRUE|FALSE}_OR_POP
            branch = ""
            if self.op_name.startswith("JUMP_IF_"): branch = state.peek()
            if self.op_name.startswith("POP_JUMP_IF_"): branch = state.pop()
            if self.op_name.endswith("_TRUE"): branch = "!" + branch
            
            # The difficulty here is that we don't always know whether a given JUMP is a loop 
            # break/continue or part of an if / elif / else.
            
            # XXX Also, differences between opcode layout in 2.6 and 2.7 ... which come down
            # to POP_JUMP_IF_*.  This leads to the "self.value-3" and "self.value+2" 
            # below, neither of which I'm happy about.
            
            # XXX If this instruction is a JUMP_ABSOLUTE back to the top of block
            # and the next instruction is a POP_BLOCK, we should suppress both
            # the continue and the break at the end of the loop.
            
            label = self.codefunc.block_start(self.value-3) or self.codefunc.block_start(self.value)
            if label:
                if branch: self.codeb = "if (!%s) continue %s" % (branch, label)
                else: self.codeb = "continue %s;" % label 
            else:
                label = self.codefunc.block_end(self.value+2) or self.codefunc.block_end(self.value+1)
                if label:
                    if branch: self.codeb = "if (!%s) break %s;" % (branch, label)
                    else: self.codeb = "break %s;" % label
                else:
                    if branch:
                        self.codea = "if (%s) {" % branch
                        self.codefunc.codeops[self.value].codea = "}"
                    else:
                        self.codea = "else {"
                        self.codefunc.codeops[self.value].codea = "}"
            
            if not branch:
                state.offset = self.value
            else:
                xstate = State(state, self.value)
                return [ state, xstate ]
            
        else:
            raise NotImplementedError("UNKNOWN OP %s" % self.op_name)
    
        return [ state ]
    
    def jscode(self, debug=False):
        if debug:
            return "/* %4d %-30s */ %s" % (
                self.offset,
                self.op_name + " " + ("" if self.value is None else repr(self.value)),
                self.codea + self.codeb,
            )
        else:
            return self.codea + self.codeb

    
class CodeFunction:
    """Represents a function or lambda, converting it to code."""
    
    def __init__(self, code_obj, prefix="$P"):
    
        # XXX some of the operators may need to know this to call
        # builtins, maybe it should become a global or maybe they
        # need to get more specialized themselves (inner classes?)
        self.prefix = prefix
        self.blocks = []
        
        self.funcname = self.label(code_obj.co_name)
        self.params = [ self.label(x) for x in code_obj.co_varnames[0:code_obj.co_argcount] ]
        self.varnames = [ self.label(x) for x in code_obj.co_varnames[code_obj.co_argcount:] ]
        
        # XXX don't forget other constant code objects, eh?
        self.consts = [ repr(x) if x is not None else 'null' for x in code_obj.co_consts ]
        
        disassy = disx.disassemble(code_obj)
        
        self.codeops = [ None ] * len(code_obj.co_code)
        
        for offset, op_code, op_name, op_args, etype, extra in disassy:
            if etype == 'const':
                value = self.consts[op_args]
            elif etype in ('name', 'local', 'global', 'free'):
                value = self.label(extra)
            elif etype:
                value = extra
            else:
                value = op_args
            
            newcodeop = CodeOp(self, offset, op_name, value)
            
            
            self.codeops[offset] = CodeOp(self, offset, op_name, value)
        
        states = [ State() ]
        for state in states:
            curop = self.codeops[state.offset]
            newstates = curop.execute(state)
            for newstate in newstates:
                if not self.codeops[newstate.offset].visited: states.append(newstate)
            
            
    def jscode(self, debug=False):
        yield "function %s (%s) {" % (self.funcname, ",".join(self.params))
        if debug and self.consts[0] is not None:
            yield "/* %s */" % self.consts[0]
        if self.varnames: yield ("var " + ",".join(self.varnames) + ";")
        for codeop in self.codeops:
            if codeop and (debug or codeop.codea or codeop.codeb):
                yield codeop.jscode(debug=debug)
        yield "}"
    
    _templabel_count = 0
    def templabel(self):
        self._templabel_count += 1
        return "%s%d" % (self.prefix, self._templabel_count)
    
    def label(self, name):
        if name.startswith("_[") and name.endswith("]"):
            return "$P$%s" % name[2:-1]
        else:
            return "%s%s" % (self.prefix, name)

    
    # XXX storing these as anonymous tuples is bloody awful.
    # Should be some kind of sensible structure here.
    
    def block_add(self, start, end, is_iter=False):
        label = self.templabel()
        self.blocks.insert(0, [label, start, end, is_iter])
        return label
    
    def block_inner(self, offset, find_iter=False):
        for block in self.blocks:
            if block[1] <= offset <= block[2] and block[3] is False or find_iter is True:
                return block[0:3]
        return (None, None, None)
    
    def block_start(self, offset):
        for block in self.blocks:
            if block[1] == offset: return block[0]
        return None
    
    def block_end(self, offset):
        for block in self.blocks:
            if block[2] == offset: return block[0]
        return None
    
    def block_either(self, offset):
        for block in self.blocks:
            if block[1] == offset or block[2] == offset: return block[0]
        return None
        
def transform_js(func, debug=False):
    codefunc = CodeFunction(func.func_code)
    return "\n".join(codefunc.jscode(debug=debug)) 