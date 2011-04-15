"""TROPYC: TRansform Objects from PYthon Code (into JavaScript)."""

# XXX modify this so that each instruction gets its own object and stack frame: as we go around a loop 
# the stack frames should hopefully line up.

# XXX javascript looping construct most likely is probably 
# while(1) { if (exitcondition) break; if (loopcondition) continue; break; }
# but I have to identify the loops somehow.

import sys
import disx
import pprint
import re

class Stack:
    """Holds the expression stack of the virtual machine as the CodeOps 
    execute on it.  Provides simple stack operations"""
    
    def __init__(self, copyfrom=None):
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
    
    def rot(self, n=1):
        self.stack[0:n] = self.stack[n-1::-1]

    def dup(self, n=1):
        self.stack[0:0] = self.stack[0:n]

    def is_empty(self):
        return len(self.stack) == 0
            
        
    
# This list is from
# * https://developer.mozilla.org/en/JavaScript/Reference/Reserved_Words
# * http://docstore.mik.ua/orelly/webprog/jscript/ch02_08.htm
# XXX are there any others needed to avoid upsetting the browser?
# XXX or should I just mangle everything to $foo or something!

ReservedWords = set('''
    abstract arguments array boolean break byte case catch char
    class const continue date debugger decodeuri decodeuricomponent
    default delete do double else encodeuri enum error escape eval
    evalerror export extends false final finally float for function
    goto if implements import in infinity instanceof int interface
    isfinite isnan let long math nan native new null number object
    package parsefloat parseint private protected public rangeerror
    referenceerror regexp return short static string super switch
    synchronized syntaxerror this throw throws transient true try
    typeerror typeof undefined unescape urierror var void
    volatile while with yield
'''.split())


# XXX need something along these lines to restrict which JavaScript
# globals are allowed through ... the compiler should barf on any 
# other globals.

AllowedGlobals = set('''
    alert document false float int max min null str true window 
'''.split())
    

def name_mangle(name):
    """Mangle identifiers to avoid collision with JavaScript reserved words."""
    # XXX could be a lot more neaterer
    
    # These "_[1]" identifiers are used in list comprehensions somehow.
    if name.startswith("_[") and name.endswith("]"): return "_Q" + name[2:-1]

    # We're reserving _[A-Z] so move anything already there out of the way. 
    if re.match("_+[A-Z]", name): return "_" + name
    
    if name.lower() in ReservedWords:
        return "_R" + name
    
    return name



_temp_var = 0
def temp_var():
    """Returns a unique(ish) name for a temporary variable."""
    # XXX there is probably a safer, saner way to do this.
    _temp_var += 1
    return "_T%d" % _temp_var



# Translate Opcode names to Javascript operators.
# XXX Sure would be nice to include precedence here.

UnaryOperatorFormats = {
    'positive': '(+{0})',
    'negative': '(-{0})',
    'not':      '(!{0})',
    'convert':  'repr({0})',  # XXX not actually supported (yet)
}

BinaryOperatorFormats = {
    'power':        '({0}**{1})',
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
        
        self.code = ""

        self.nextoffs = None
        self.jumpoffs = None
        
        self.visited = False
        
    def execute(self, state):
        """Run this op, mutating state in the process."""
        
        # XXX There are much nicer ways to structure this than a giant "elif"
        
        # PURE FUNCTIONAL STUFF
        
        self.nextoffs = self.offset + (3 if self.value else 1)
        self.jumpoffs = None
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
        elif self.op_name == 'DUP_TOP':   state.dup()             # XXX check this is okay.
        elif self.op_name == 'DUP_TOPX':  state.dup(self.value)   # XXX this too.
        
        elif self.op_name == 'ROT_TWO':   state.rot(2)
        elif self.op_name == 'ROT_THREE': state.rot(3)
        elif self.op_name == 'ROT_FOUR':  state.rot(4)
        
        elif self.op_name == 'SLICE+0':   state.push("%s.slice()" % state.pop())
        elif self.op_name == 'SLICE+1':   state.push("%s.slice(%s)" % state.pop2())
        elif self.op_name == 'SLICE+2':   state.push("%s.slice(0,%s)" % state.pop2())
        elif self.op_name == 'SLICE+3':   state.push("%s.slice(%s,%s)" % state.popn(3))

        elif self.op_name in ('BUILD_LIST', 'BUILD_TUPLE'): 
            ll = reversed(state.popn(self.value))
            state.push("[" + ",".join(ll) + "]")
            
        elif self.op_name == 'BUILD_MAP': state.push("{}")

        elif self.op_name in ('STORE_NAME', 'STORE_FAST'): self.code = "%s = %s;" % (self.value, state.pop())
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
            self.code = "%s.%s = %s" % (obj, self.value, val)

        elif self.op_name == 'UNPACK_SEQUENCE':
            tos = state.pop()
            for n in range(0, self.value):
                # XXX Do we need to use temp values ?            
                #temp = temp_var(n)
                #self.code += "var %s = %s[%d];" % (temp, tos, n)
                #state.push(temp)
                state.push("%s[%d]" % (tos, n))
    
        # ACTUALLY GENERATE SOME CODE!
        
        elif self.op_name == 'PRINT_ITEM': self.code += "print(%s);" % state.pop()
        elif self.op_name == 'PRINT_NEWLINE': self.code += "print('-----');"
        elif self.op_name in ('DELETE_NAME', 'DELETE_FAST'): self.code += "delete %s;" % self.value
        elif self.op_name == 'LIST_APPEND': self.code += "%s.push(%s);" % state.pop2()
        elif self.op_name == 'DELETE_ATTR': self.code += "delete %s.%s;" % (self.value, state.pop())
        
        elif self.op_name == 'RETURN_VALUE':
            self.code += "return %s;" % state.pop()
            self.nextoffs = None
            
        elif self.op_name == 'CALL_FUNCTION':
            # XXX we don't handle kwargs yet
            kwargs = state.popn(int(self.value / 256) * 2)      
            args = state.popn(self.value % 256)
            func = state.pop()
            
            # Functions are always saved rather than added to 
            # the expression state because that way we know they'll
            # actually get run right away.
            # XXX it would be nice to optimize away void functions (followed by POP_TOP).
            # XXX or functions immediately followed by a STORE.
            temp = self.codefunc.templabel()
            self.code += "var %s = %s(%s);" % (temp, func, ",".join(args))
            state.push(temp)
        
        #elif self.op_name == 'RAISE_VARARGS':
        #    ll = state.popn(self.value)
        #    self.code = "raise (%s);" % ",".join(ll)
        
        # LOOPING AND BRANCHING
        
        elif self.op_name == 'SETUP_LOOP':
            self.jumpoffs = self.value
            label = self.codefunc.block_add(self.offset, self.value)
            self.code += "%s: while (1) {" % label
            
        elif self.op_name == 'GET_ITER':
            iterable = state.pop()
            temp = self.codefunc.templabel()
            self.code += "var %s = %s;" % (temp, iterable)
            state.push(temp)
            
        elif self.op_name == 'FOR_ITER':
            self.jumpoffs = self.value
            label = self.codefunc.block_mod(self.offset, self.value)
            iterator = state.peek()
            temp = self.codefunc.templabel()
            self.code += "%s: for (var %s in %s) {" % (label, temp, iterator)  
            state.push("%s[%s]" % (iterator, temp))
            
        elif self.op_name == 'POP_BLOCK':
            self.code += "break; }"
            
        elif self.op_name == 'CONTINUE_LOOP':
            label, end = state.find_loop(self.value - 3, end=False)
            self.code += "continue %s;" % label

        elif self.op_name == 'BREAK_LOOP':
            label, start, end = self.codefunc.block_inner(offset)
            self.code += "break %s;" % label
            self.nextoffs = end
        
        elif self.op_name.startswith("JUMP_") or self.op_name.startswith("POP_JUMP_"):
            branch = ""
            if self.op_name.startswith("JUMP_IF_"): branch = state.peek()
            if self.op_name.startswith("POP_JUMP_IF_"): branch = state.pop()
            if self.op_name.endswith("_FALSE"): branch = "!" + branch
            if branch: branch = "if (%s) " % branch
            
            # The difficulty here is that we don't always know whether a given JUMP is a loop 
            # break/continue or part of an if / elif / else.
            
            # XXX Also, differences between opcode layout in 2.6 and 2.7 ... which come down
            # to POP_JUMP_IF_*
            
            label = self.codefunc.block_start(self.value-3) or self.codefunc.block_start(self.value)
            if label:
                self.code += branch + "continue %s;" % label 
            else:
                label = self.codefunc.block_end(self.value+2) or self.codefunc.block_end(self.value+1)
                if label:
                    self.code += branch + "break %s;" % label
                else:
                    if branch:
                        self.code += branch + " {"
                    else:
                        self.code += "} else {"
                        self.codefunc.codeops[self.value].code = "} " + self.codefunc.codeops[self.value].code
            
            if not branch:
                self.nextoffs = self.value
            else:
                self.jumpoffs = self.value
                
        else:
            print "UNKNOWN OP %s" % self.op_name
    
    
class CodeFunction:
    """Represents a function or lambda, converting it to code."""
    
    def __init__(self, code_obj, prefix="$P"):
    
        self.prefix = prefix
        self.blocks = []
        
        self.funcname = self.label(code_obj.co_name)
        self.params = [ self.label(x) for x in code_obj.co_varnames[0:code_obj.co_argcount] ]
        self.varnames = [ self.label(x) for x in code_obj.co_varnames[code_obj.co_argcount:] ]
        
        # XXX don't forget other constant code objects, eh?
        consts = [ repr(x) for x in code_obj.co_consts ]
        
        disassy = disx.disassemble(code_obj)
        
        self.codeops = [ None ] * len(code_obj.co_code)
        
        for offset, op_code, op_name, op_args, etype, extra in disassy:
            if etype == 'const':
                value = consts[op_args]
            elif etype in ('name', 'local', 'global', 'free'):
                value = self.label(extra)
            elif etype:
                value = extra
            else:
                value = op_args
            
            newcodeop = CodeOp(self, offset, op_name, value)
            
            
            self.codeops[offset] = CodeOp(self, offset, op_name, value)
        
        cursors = [ (0, Stack()) ]
        for offset, stack in cursors:
            curop = self.codeops[offset]
            curop.execute(stack)
            if curop.nextoffs and not self.codeops[curop.nextoffs].visited: cursors.append( (curop.nextoffs, stack) )
            if curop.jumpoffs and not self.codeops[curop.nextoffs].visited: cursors.append( (curop.jumpoffs, Stack(stack)) )
            
    def jscode(self):
        yield "function %s (%s) {" % (self.funcname, ",".join(self.params))
        for varname in self.varnames:
            yield "var %s;" % varname
        for codeop in self.codeops:
            if codeop: yield "/* %6d %-20s */ %s" % (codeop.offset, "%s %s" % (codeop.op_name, codeop.value), codeop.code if codeop.code else "")
            #if codeop and codeop.code: yield "\t" + codeop.code
        yield "}"
    
    def label(self, name):
        return "%s%s" % (self.prefix, name)

    _templabel_count = 0
    def templabel(self):
        self._templabel_count += 1
        return "%s%d" % (self.prefix, self._templabel_count)
    
    def block_add(self, start, end):
        label = self.templabel()
        self.blocks.insert(0, [label, start, end])
        return label
    
    def block_mod(self, start=None, end=None):
        self.codeops[self.blocks[0][1]] = ""
        if start is not None: self.blocks[0][1] = start
        if end is not None: self.blocks[0][2] = end
        return self.blocks[0][0]
        
    def block_inner(self, offset):
        for block in self.blocks:
            if block[1] <= offset <= block[2]:
                return block
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
        
