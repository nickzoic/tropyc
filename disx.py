"""An improved Python byte code disassembler."""

import sys
import types
import opcode
import dis
import json

class Stack:
    
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


    

class CodeTransformer:

    def __init__(self, code_obj):
        self.code_obj = code_obj
        self.stack = Stack()
        
    def emit(self, code):
        print "%s;" % code
        
    def unary_op(self, operator, pre="(", post=")"):
        a = self.stack.pop()
        self.stack.push(''.join((pre,operator,a,post)))
        
    def binary_op(self, operator, pre="(", post=")"):
        a,b = self.stack.pop2()
        self.stack.push(''.join((pre,a,operator,b,post)))
    
    def save_stack(self):
        # XXX hopefully not necessary, def. not optimal!
        for n, e in enumerate(self.stack):
            self.emit("var _s%d = %s" % (n, e))
        nn = len(self.stack)
        self.stack = ["_s%d" % n for n in range(0,nn)]
    
    temp_counter = 0
    
    def make_temp(self):
        self.temp_counter += 1
        return "_t%d" % self.temp_counter
        
    #--- opcodes
    
    def stop_code(self, op):
        pass
    
    def nop(self, op):
        pass
    
    def pop_top(self):
        self.stack.pop()
        
    def rot_two(self):
        self.stack.rot(2)
        
    def rot_three(self):
        self.stack.rot(3)
    
    def rot_four(self):
        self.stack.rot(4)
        
    def dup_top(self):
        # XXX needs to work out if tos is an expression or not
        tos = self.stack.pop()
        temp = self.make_temp()
        self.emit("var %s = %s" % (temp, tos))
        self.stack.push(temp)
        self.stack.push(temp)
    
    def unary_positive(self):
        self.unary_op('+')
        
    def unary_negative(self):
        self.unary_op('-')

    def unary_not(self):
        self.unary_op('!')

    def unary_convert(self):
        # XXX repr isn't real javascript, not actually implemented yet!
        self.unary_op('', 'repr(')

    def unary_invert(self):
        self.unary_op('~')
        
    # def get_iter(self):
      
    def binary_power(self):
        self.binary_op('**')
    
    def binary_multiply(self):
        self.binary_op('*')
    
    def binary_floor_divide(self):
        self.binary_op("/", "Math.floor(")

    binary_divide = binary_floor_divide
    
    def binary_true_divide(self):
        self.binary_op('/')
        
    def binary_modulo(self):
        self.binary_op('%')
    
    def binary_add(self):
        self.binary_op('+')
    
    def binary_subtract(self):
        self.binary_op('-')
        
    def binary_lshift(self):
        self.binary_op('<<')
    
    def binary_rshift(self):
        self.binary_op('>>')

    def binary_and(self):
        self.binary_op('&')
        
    def binary_xor(self):
        self.binary_op('^')
    
    def binary_or(self):
        self.binary_op('|')
    
    # inplace_* is currently mapped to binary_*
    
    def slice_0(self):
        self.stack.unary_op("","",".slice()")
    
    def slice_1(self):
        tos, tos1 = self.stack.pop2()
        self.stack.push("%s.slice(%d)" % (tos1, tos))
        
    def slice_2(self):
        tos, tos1 = self.stack.pop2()
        self.stack.push("%s.slice(0,%d)" % (tos1, tos))

    def slice_3(self):
        tos, tos1, tos2 = self.stack.popn(3)
        self.stack.push("%s.slice(%d,%d)" % (tos2, tos1, tos))
    
    # store_slice_* and delete_slice_* I'll worry about later
    
    def print_item(self):
        tos = self.stack.pop()
        self.emit("console.log(%s)" % tos)
    
    def print_newline(self):
        self.emit("console.log('-----')")
    
    def return_value(self):
        tos = self.stack.pop()
        self.emit("return %s" % tos)
        
    def store_name(self, n):
        self.emit("%s = %s" % (self.code_obj.co_names[n], self.stack.pop()))

    def delete_name(self, n):
        self.emit("delete %s" % self.code_obj.co_names[n])
        
    def dup_topx(self, n):
	# XXX should do something cleverer like dup_top?
        self.stack.dup(n)
        
    def load_const(self, n):
	# XXX consts can include code objects for lambdas
	# and nested functions
        self.stack.push(json.dumps(self.code_obj.co_consts[n]))
        
    def load_name(self, n):
        self.stack.push(self.code_obj.co_names[n])
        
    def build_tuple(self, n):
        ll = self.stack.popn(n)
        self.stack.push("[" + ",".join(ll) + "]")
    
    build_list = build_tuple
    
    def build_map(self, n):
        self.stack.push("{}")
    
    def store_map(self):
        k, v, m = self.stack.popn(3)
        if m == '{}':
            self.stack.push("{%s:%s}" % (k,v))
        elif m.endswith("}"):
            self.stack.push(m[:-1] + ",%s:%s" % (k,v) + "}")
        else:
            # XXX does this ever happen?
            self.stack.push(m)
            self.emit("%s[%s] = %s" % (m,k,v))
    
    def compare_op(self, n):
        # XXX missing a couple of cases
        op = opcode.cmp_op[n]
        if op == 'in':
            self.binary_op(" in ")
        elif op == 'not in':
            self.binary_op(" in ", "!(")
        elif op == 'is':
            self.binary_op("===")
        elif op == 'is not':
            self.binary_op("!==")
        else:
            self.binary_op(op)
    
    def jump_forward(self, n):
        self.emit("goto %d" % n)
        
    def jump_if_true(self, n):
        tos = self.stack.peek()
        self.emit("if %s goto %d" % (tos, n))

    def jump_if_false(self, n):
        tos = self.stack.peek()
        self.emit("if (!%s) goto %d" % (tos, n))

    def jump_absolute(self, n):
        self.emit("goabs %d" % n)
    
    def load_global(self, n):
        self.stack.push("%s" % self.code_obj.co_names[n])
        
    def load_fast(self, n):
        varname = self.code_obj.co_varnames[n]
        if varname.startswith("_["): varname = "_f%s" % varname[2:-1]
        self.stack.push(varname)
        
    def store_fast(self, n):
        varname = self.code_obj.co_varnames[n]
        if varname.startswith("_["): varname = "_f%s" % varname[2:-1]
        vardecl = "var " if n >= self.code_obj.co_argcount else ""
        self.emit("%s%s = %s" % (vardecl, varname, self.stack.pop()))
    
    def delete_fast(self, n):
        varname = self.code_obj.co_varnames[n]
        if varname.startswith("_["): varname = "_f%s" % varname[2:-1]
        self.emit("delete %s" % varname);
    
    def call_function(self, n):
        # XXX key params
        key_params_list = self.stack.popn((n / 256) * 2)
        key_params_list.reverse()
        key_params_pairs = zip(key_params_list[0::2], key_params_list[1::2])
        key_params_str = "{" + ','.join(["%s:%s" % (k,v) for k,v in key_params_pairs]) + "}," if key_params_list else ""

        pos_params_list = reversed(self.stack.popn(n % 256))
        pos_params_str = ",".join(pos_params_list)
        
        func = self.stack.pop()

        # XXX it would be great to optimize void functions away
        # instead of temp variabling them
        temp = self.make_temp()
        self.emit("var %s = %s(%s%s)" % (temp, func, key_params_str, pos_params_str))
        self.stack.push(temp)

    def list_append(self):
        self.emit("%s.append(%s)" % self.stack.pop2())
    
    def load_attr(self, n):
        tos = self.stack.pop()
        self.stack.push("%s.%s" % (tos, self.code_obj.co_names[n]))
   
    #-----
    
    def despatch(self, op, op_arg=None):
        op_name = opcode.opname[op].lower().replace('+', '_')
        if op_name.startswith("inplace_"):
            op_name = op_name.replace("inplace_", "binary_")
            
        if hasattr(self, op_name):
            if op_arg is not None:
                getattr(self, op_name)(op_arg)
            else:
                getattr(self, op_name)()
        else:
            print "Unknown Opcode %s" % op_name
    
    def analyse(self):
        '''Make a first pass through the code and split out the instructions'''
        code = self.code_obj.co_code
        cur_code = 0
        extended_arg = 0
        
        self.ops = [ None ] * len(code)
        
        while cur_code < len(code):
            op = ord(code[cur_code])
            op_arg = None
            
            if op >= opcode.HAVE_ARGUMENT:
                op_arg = ord(code[cur_code+1]) + ord(code[cur_code+2])*256 + extended_arg
                
                extended_arg = 0                
                if op == opcode.EXTENDED_ARG:
                    extended_arg = op_arg*65536L
                else:
                    self.ops[cur_code] = (op, op_arg)
                    
                cur_code += 3
            else:
                self.ops[cur_code] = (op, None)
                cur_code += 1
        
            
            self.despatch(op, op_arg)
    
    

def bar(a):
        return a * 2

def foo(x):


    return bar(x)

    
print dis.dis(foo)

x = CodeTransformer(foo.func_code)
x.analyse()
