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
    
# This list is from
# * https://developer.mozilla.org/en/JavaScript/Reference/Reserved_Words
# * http://docstore.mik.ua/orelly/webprog/jscript/ch02_08.htm
# XXX are there any others needed to avoid upsetting the browser?
# XXX or should I just mangle everything to $foo or something!

ReservedWords = set(
    "abstract arguments array boolean break byte case catch char \
    class const continue date debugger decodeuri decodeuricomponent \
    default delete do double else encodeuri enum error escape eval \
    evalerror export extends false final finally float for function \
    goto if implements import in infinity instanceof int interface \
    isfinite isnan let long math nan native new null number object \
    package parsefloat parseint private protected public rangeerror \
    referenceerror regexp return short static string super switch \
    synchronized syntaxerror this throw throws transient true try \
    typeerror typeof undefined unescape urierror var void \
    volatile while with yield".split()
)

def name_mangle(name):
    """Mangle identifiers to avoid collision with JavaScript reserved words."""
    if name.startswith("_[") and name.endswith("]"): return "_q" + name[2:-1]
    if name.startswith("_"): return "_" + name
    if name.lower() in ReservedWords:
        return "_R" + name
    return name



_temp_var = 0
def temp_var():
    """Returns a unique(ish) name for a temporary variable."""
    _temp_var += 1
    return "_T%d" % _temp_var



# Translate Opcode names to Javascript operators.
# XXX Sure would be nice to include precedence here.

UnaryOperatorFormats = {
    'positive': '(+{0})',
    'negative': '(-{0})',
    'not':      '(!{0})',
    'convert':  'repr({0})',  # XXX not actually supported
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

    def __init__(self, codefunc, op_name, value):
        """codefunc: the parent function block.
        op_name: the name of this operator.
        value: operator parameter, suitably decoded. 
        """
        
        self.codefunc = codefunc
        self.op_name = op_name
        self.value = value
            
        self.code = ""

    def find_branches(self):
        
        if self.op_name.startswith('POP_JUMP_IF') or self.op_name.startswith('JUMP_IF'):
            self.goto = [ codefunc.codeops[]
        elif self.op_name.startswith('JUMP_'):
            
            
    def run_stack(self, stack):
        
        # NOPs
        
        if self.op_name == 'NOP':
            pass

        # PUSH new stuff onto stack
        
        elif self.op_name in ('LOAD_CONST', 'LOAD_NAME', 'LOAD_FAST', 'LOAD_GLOBAL'): stack.push(self.value)
        
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
        elif self.op_name == 'DUP_TOP':   stack.dup()             # XXX check this is okay.
        elif self.op_name == 'DUP_TOPX':  stack.dup(self.value)   # XXX this too.
        elif self.op_name == 'ROT_TWO':   stack.rot(2)
        elif self.op_name == 'ROT_THREE': stack.rot(3)
        elif self.op_name == 'ROT_FOUR':  stack.rot(4)
        
        elif self.op_name == 'SLICE+0':   stack.push("%s.slice()" % stack.pop())
        elif self.op_name == 'SLICE+1':   stack.push("%s.slice(%s)" % stack.pop2())
        elif self.op_name == 'SLICE+2':   stack.push("%s.slice(0,%s)" % stack.pop2())
        elif self.op_name == 'SLICE+3':   stack.push("%s.slice(%s,%s)" % stack.popn(3))

        elif self.op_name in ('BUILD_LIST', 'BUILD_TUPLE'): 
            ll = stack.popn(self.value)
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
        
        elif self.op_name == 'PRINT_ITEM': self.code = "print(%s)" % stack.pop()
        elif self.op_name == 'PRINT_NEWLINE': self.code = "print('-----')"
        elif self.op_name in ('STORE_NAME', 'STORE_FAST'): self.code = "%s = %s" % (self.value, stack.pop())
        elif self.op_name in ('DELETE_NAME', 'DELETE_FAST'): self.code = "delete %s" % self.value
        elif self.op_name == 'RETURN_VALUE': self.code = "return %s" % stack.pop()
        elif self.op_name == 'LIST_APPEND': self.code = "%s.push(%s)" % stack.pop2()
        elif self.op_name == 'DELETE_ATTR': self.code = "delete %s.%s" % (self.value, stack.pop())
        
        elif self.op_name == 'STORE_ATTR':
            val, obj = stack.pop2()
            self.code = "%s.%s = %s" % (obj, self.value, val)
        
        elif self.op_name == 'CALL_FUNCTION':
            # XXX we don't handle kwargs
            kwargs = stack.popn(int(self.value / 256) * 2)      
            args = stack.popn(self.value % 256)
            func = stack.pop()
            
            # XXX it would be nice to optimize away void functions (followed by POP_TOP).
            # XXX or functions immediately followed by a STORE.
            # XXX actually, maybe I do the opposite and only assign to a variable on DUP
            # XXX and emit on POP!
            temp = temp_var()
            self.code = "var %s = %s(%s)" % (temp, func, ",".join(args))
            stack.push(temp)
        
        elif self.op_name == 'UNPACK_SEQUENCE':
            # XXX Do we ever actually need the temp values?
            # XXX Or are they always used in expressions?
            tos = stack.pop()
            for n in range(0, self.value):
                temp = temp_var(n)
                self.code += "var %s = %s[%d]" % (temp, tos, n)
                stack.push(temp)
        
        elif self.op_name in ('JUMP_FORWARD', 'JUMP_ABSOLUTE'):
            self.code = "goto %s" % self.value
            
        elif self.op_name == 'JUMP_IF_TRUE': self.code = "if (%s) goto %s" % (stack.peek(), self.value)
        elif self.op_name == 'POP_JUMP_IF_TRUE': self.code = "if (%s) goto %s" % (stack.pop(), self.value)
        elif self.op_name == 'JUMP_IF_FALSE': self.code = "if (!%s) goto %s" % (stack.peek(), self.value)
        elif self.op_name == 'POP_JUMP_IF_FALSE': self.code = "if (!%s) goto %s" % (stack.pop(), self.value)
            
        elif self.op_name == 'RAISE_VARARGS':
            ll = stack.popn(self.value)
            self.code = "raise (%s)" % ",".join(ll)
            
        else:
            print "UNKNOWN OP %s" % self.op_name
            
    
    
class CodeFunc:
    """Represents a function or lambda, converting it to code."""
    
    def __init__(self, code_obj):
    
        disassy = disx.disassemble(code_obj)
        
        self.codeobj = [ None ] * len(code_obj.co_code)
        
        # XXX don't forget other constant code objects, eh?
        consts = [ repr(x) for x in code_obj.co_consts ]
        
        self.codeobjs = []
        for offset, op_code, op_name, op_args, etype, extra in disassy:
            if etype == 'const':
                value = consts[op_args]
            elif etype in ('name', 'global', 'local', 'free'):
                value = repr(self.extra)
            elif etype:
                value = extra
            else:
                value = op_args
            
            self.codeobj[offset] = CodeOp(self, op_name, value)
           
    
    
        
def f(x):
    if y > 0:
        print "yay!"
    if x > 0: 
        a = x + 1
    elif x < 0:
        a = x - 1
    else:
        a = "FUCK!"
    return a

pprint.pprint(disx.dis(f))
CodeFunc(f.func_code)