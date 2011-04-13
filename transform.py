"""Transform Python Byte Code into JavaScript."""

# XXX modify this so that each instruction gets its own object and stack frame: as we go around a loop 
# the stack frames should hopefully line up.

# XXX javascript looping construct most likely is probably 
# while(1) { if (exitcondition) break; if (loopcondition) continue; break; }
# but I have to identify the loops somehow.

import sys
import disx
import pprint
import dis

class Stack:
    """A simple stack class specialized to handle the operations we need
    in the virtual machine.  Might make more sense to turn the list the 
    other way up if that's quicker, but python stack never gets very deep
    anyway."""
    
    def __init__(self, copyfrom=[]):
        self.stack = copyfrom[:]

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

    def rot(self, n=1):
        self.stack[0:n] = self.stack[n-1::-1]

    def dup(self, n=1):
        self.stack[0:0] = self.stack[0:n]

    def is_empty(self):
        return len(self.stack) == 0
    
# This list is from https://developer.mozilla.org/en/JavaScript/Reference/Reserved_Words
# XXX add in words from http://docstore.mik.ua/orelly/webprog/jscript/ch02_08.htm
# XXX are there any others needed to avoid upsetting the browser?

ReservedWords = set(
    "break case catch class const continue debugger default delete do else enum export extends \
    false finally for function if implements import in instanceof interface let new null package private \
    protected public return static super switch this throw true try typeof var void while with yield".split()
)

def name_mangle(name):
    """Mangle identifiers to avoid collision with JavaScript reserved words."""
    if name.startswith("_[") and name.endswith("]"): return "_q" + name[2:-1]
    if name.startswith("_"): return "_" + name
    if lc(name) in ReservedWords:
        return "_r" + name
    return name


# Translate Opcode names to Javascript operators.

UnaryOperatorFormats = {
    'positive': '(+{0})',
    'negative': '(-{0})',
    'not': '(!{0})'
}

BinaryOperatorFormats = {
    'power': '({0}**{1})',
    'multiply': '({0}*{1})',
    'divide': 'Math.floor({0}/{1})',
    'floor_divide': 'Math.floor({0}/{1})',
    'true_divide': '({0}/{1})',
    'modulo': '({0}%{1})',
    'add': '({0}+{1})',
    'subtract': '({0}-{1})',
    'subscr': '({0}[{1}])',
    'lshift': '({0}<<{1})',
    'rshift': '({0}>>{1})',
    'and': '({0}&{1})',
    'xor': '({0}^{1})',
    'or': '({0}|{1})',
}

CompareOperatorFormats = {
    '<': '({0}<{1})',
    '<=': '({0}<={1})',
    '==': '({0}=={1})',
    '>=': '({0}>={1})',
    '>': '({0}>{1})',
    '!=': '({0}!={1})',
    'in': '({0} in {1})',
    'not in': '!({0} in {1})',
    'is': '({0} === {1})',
    'is not': '({0} !== {1})',
}
    
    
class CodeOp:
    """Really just a container for the opcode"""
    def __init__(self, offset, op_code, op_name, op_arg, etype, extra):
        
        self.offset = offset
        self.op_code = op_code
        self.op_name = op_name
        self.op_arg = op_arg
        self.etype = etype
        self.extra = extra
        self.code = ""

    def tempvar(self, n=None):
        # XXX would this be better as a generator or something?
        if n is None: return "_T%d" % self.offset
        else: return "_T%d_%s" % (self.offset, n)
        
    def decompile(self, stack):
        
        # NOPs
        
        if self.op_name == 'NOP':
            pass

        # PUSH new stuff onto stack
        
        elif self.op_name in ('LOAD_CONST', 'LOAD_NAME', 'LOAD_FAST', 'LOAD_GLOBAL'): stack.push(self.extra)
        
        # PURE FUNCTIONAL
        
        elif self.op_name.startswith('UNARY_'):
            operator = lc(self.op_name[self.op_name.find("_")+1:])                        
            stack.push(UnaryOperatorFormats[operator].format(stack.pop()))
            
        elif self.op_name.startswith('BINARY_') or self.op_name.startswith('INPLACE_'):
            operator = self.op_name[self.op_name.find("_")+1:].lower()
            stack.push(BinaryOperatorFormats[operator].format(*stack.pop2()))
            
        elif self.op_name == 'COMPARE_OP':
            tos, tos1 = stack.pop2()
            stack.push(CompareOperatorFormats[self.extra].format(tos, tos1))
        
        elif self.op_name == 'POP_TOP':   stack.pop()    
        elif self.op_name == 'DUP_TOP':   stack.dup()
        elif self.op_name == 'ROT_TWO':   stack.rot(2)
        elif self.op_name == 'ROT_THREE': stack.rot(3)
        elif self.op_name == 'ROT_FOUR':  stack.rot(4)
        
        elif self.op_name == 'SLICE+0':   stack.push("%s.slice()" % stack.pop())
        elif self.op_name == 'SLICE+1':   stack.push("%s.slice(%s)" % stack.pop2())
        elif self.op_name == 'SLICE+2':   stack.push("%s.slice(0,%s)" % stack.pop2())
        elif self.op_name == 'SLICE+3':   stack.push("%s.slice(%s,%s)" % stack.popn(3))

        elif self.op_name in ('LOAD_LIST', 'LOAD_TUPLE'): 
            ll = stack.popn(self.op_arg)
            stack.push("[" + ",".join(ll) + "]")
            
        elif self.op_name == 'LOAD_ATTR':
            stack.push("%s.%s" % (self.extra, stack.pop()))

        elif self.op_name == 'BUILD_MAP': stack.push("{}")
        elif self.op_name == 'STORE_MAP':
            k, v, m = stack.popn(3)
            if m == '{}':
                self.stack.push("{%s:%s}" % (k,v))
            elif m.endswith("}"):
                self.stack.push(m[:-1] + ",%s:%s" % (k,v) + "}")
            else:
                raise NotImplementedError("Trying to STORE_MAP to something not a hash?")
            
        # ACTUALLY EMIT CODE!
        
        elif self.op_name in ('STORE_NAME', 'STORE_FAST'): self.code = "%s = %s" % (self.extra, stack.pop())
        elif self.op_name in ('DELETE_NAME', 'DELETE_FAST'): self.code = "delete %s" % self.extra
        elif self.op_name == 'RETURN_VALUE': self.code = "return %s" % stack.pop()
        elif self.op_name == 'LIST_APPEND': self.code = "%s.push(%s)" % stack.pop2()
        elif self.op_name == 'DELETE_ATTR': self.code = "delete %s.%s" % (self.extra, stack.pop())
        
        elif self.op_name == 'STORE_ATTR':
            val, obj = stack.pop2()
            self.code = "%s.%s = %s" % (obj, self.extra, val)
        
        elif self.op_name == 'CALL_FUNCTION':
            # XXX we don't handle kwargs
            kwargs = stack.popn(int(self.op_arg / 256) * 2)      
            args = stack.popn(self.op_arg % 256)
            func = stack.pop()
            
            # XXX it would be nice to optimize away void functions.
            temp = self.tempvar()
            self.code = "%s = %s(%s)" % (temp, func, ",".join(args))
            stack.push(temp)
        
        elif self.op_name == 'UNPACK_SEQUENCE':
            # XXX Do we ever actually need the temp values?
            # XXX Or are they always used in expressions?
            tos = stack.pop()
            for n in range(0, op_arg):
                temp = self.tempvar(n)
                self.code += "var %s = %s[%d]" % (temp, tos, n)
                stack.push(temp)
        
        elif self.op_name == 'POP_JUMP_IF_TRUE':
            tos = stack.pop()
            self.code = "if (%s) break" % tos
            
        elif self.op_name == 'POP_JUMP_IF_FALSE':
            tos = stack.pop()
            self.code = "if (!%s) break" % tos
            
        else:
            print "UNKNOWN OP %s" % self.op_name
            
class CodeLump:
    """A CodeLump is a logical group of CodeOps.  The distinguishing feature is
    that a CodeLump is stack-neutral, eg: the stack is in the same state exiting
    the CodeLump as it was entering it.  The Python 2.7 compiler actually gives
    away the location of each code lump through the co_lnotab structure, which
    has one row for each CodeLump.  If this didn't exist we'd have to work it
    out by watching the stack.  The nice thing about all this is that we DO NOT
    want to reproduce a stack machine in the target language, rather we want to
    roll the stack operations up into expressions."""
    
    def __init__(self, co, offset, length, line_no):
        
        self.codeops = [ CodeOp(*x) for x in disx.disassemble(co, offset, length) ]
        self.code = ""
        self.stack = Stack()
        
        for codeop in self.codeops:
            codeop.decompile(self.stack)
            if codeop.code:
                print codeop.code
                
        if not self.stack.is_empty():
            print "Hey, CodeLump at %d isn't stack-neutral" % offset
            
        
def lnotab_gen(co):
    offset = 0
    line_no = co.co_firstlineno
    
    # XXX a bit clumsy
    for ncode, nline in zip(
        [ord(c) for c in co.co_lnotab[0::2]],
        [ord(c) for c in co.co_lnotab[1::2]]
    ):
        if ncode:
            yield offset, ncode, line_no
            offset += ncode
        line_no += nline
    
    if len(co.co_code) > offset:
        yield offset, len(co.co_code) - offset, line_no
    
    
class CodeObject:
    
    def __init__(self, code_obj):
    
        self.lumps = [ CodeLump(code_obj, *x) for x in lnotab_gen(code_obj) ]
                    

        
def f(x):
    if x > 0: 
        return x + 1
    else:
        return 0

pprint.pprint(disx.dis(f))
CodeObject(f.func_code)