"""An improved Python byte code disassembler.  Does much the same
as the standard "dis" module, but returns a list of tuples instead."""

# XXX would it make more sense to return an object or a list of objects instead?
# A graph of objects?  Where to stop?

import opcode
import types

def line_numbers(lstart, lnotab, codelen):
     # XXX this could perhaps be nicer as a generator.
     line_numbers = []
     lnum = lstart
     
     for db, di in zip([ord(c) for c in lnotab[0::2]], [ord(c) for c in lnotab[1::2]]):
          line_numbers.extend([ lnum ] * db)
          lnum += di
     
     line_numbers.extend([ lnum ] * (codelen - len(line_numbers)))
     return line_numbers

def lnotab_gen(firstlineno, lnotab, len_code):
     cur_line = firstlineno
     cur_code = 0
     for ncode, nline in zip([ord(c) for c in lnotab[0::2]], [ord(c) for c in lnotab[1::2]]):
          yield ncode, cur_line
          cur_code += ncode
          cur_line += nline
     yield len_code - cur_code, cur_line
     
def disassemble(co, offset=0, length=None):
     """A lot like dis.disassemble but this returns a list of tuples like:
     (cur_code, op_code, op_name, op_arg, etype, extra)"""
     
     assert(type(co) is types.CodeType)

     if length is None: length = len(co.co_code) - offset
     cur_code = offset

     listing = []
     extended_arg = 0
          
     while cur_code < offset + length:
          op = ord(co.co_code[cur_code])
          
          if op < opcode.HAVE_ARGUMENT:
               listing.append((cur_code, op, opcode.opname[op], None, None, None))
               cur_code += 1     
          else:
               op_arg = ord(co.co_code[cur_code+1]) + ord(co.co_code[cur_code+2])*256 + extended_arg
               
               extended_arg = 0                
               if op == opcode.EXTENDED_ARG:
                    extended_arg = op_arg*65536L
                    continue
               elif op in opcode.hasconst:
                    etype = "const"
                    extra = co.co_consts[op_arg]
               elif op in opcode.hasname:
                    etype = "name"
                    extra = co.co_names[op_arg]
               elif op in opcode.hasjrel:
                    etype = "jump"
                    extra = cur_code + 3 + op_arg
               elif op in opcode.hasjabs:
                    etype = "jump"
                    extra = op_arg
               elif op in opcode.haslocal:
                    etype = "local"
                    extra = co.co_varnames[op_arg]
               elif op in opcode.hascompare:
                    etype = "compare"
                    extra = opcode.cmp_op[op_arg]
               elif op in opcode.hasfree:
                    etype = "free"
                    extra = (co.co_cellvars + co.co_freevars)[op_arg]
               else:
                    etype = None
                    extra = None
          
               listing.append((cur_code, op, opcode.opname[op], op_arg, etype, extra))
               cur_code += 3
               
     return listing



def dis(what):
     if type(what) is types.ClassType:
          return dict([ (x.__name__, disassemble(x.im_func.func_code)) for x in dir(what) if type(x) is types.MethodType ])
     elif type(what) is types.FunctionType:
          return disassemble(what.func_code)
     else:
          raise NotImplementedError("What's a %s?" + repr(type(what)))


     
if __name__ == '__main__':
     import pprint
     
     pprint.pprint(dis(disassemble))