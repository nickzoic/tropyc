"""An improved Python byte code disassembler.  Does much the same
as the standard "dis" module, but returns a data structure instead."""

import opcode
import types

def line_numbers(lstart, lnotab, codelen):
     line_numbers = []
     lnum = lstart
     
     for db, di in zip([ord(c) for c in lnotab[0::2]], [ord(c) for c in lnotab[1::2]]):
          line_numbers.extend([ lnum ] * db)
          lnum += di
     
     line_numbers.extend([ lnum ] * (codelen - len(line_numbers)))
     return line_numbers

def disassemble(co):
     assert(type(co) is types.CodeType)

     code = co.co_code
     cur_code = 0
     extended_arg = 0
     free = None

     lnumbers = line_numbers(co.co_firstlineno, co.co_lnotab, len(code))
     listing = []
     
     while cur_code < len(code):
          
          op = ord(code[cur_code])
          
          if op < opcode.HAVE_ARGUMENT:
               listing.append((cur_code, lnumbers[cur_code], op, opcode.opname[op], None, None, None))
               cur_code += 1     
          else:
               op_arg = ord(code[cur_code+1]) + ord(code[cur_code+2])*256 + extended_arg
               
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
               elif op in opcode.haslocal:
                    etype = "extra"
                    extra = co.co_varnames[op_arg]
               elif op in opcode.hascompare:
                    etype = "compare"
                    extra = opcode.cmp_op[op_arg]
               elif op in opcode.hasfree:
                    if free is None:
                         free = co.co_cellvars + co.co_freevars
                    etype = "free"
                    extra = free[op_arg]
               else:
                    etype = None
                    extra = None
          
               listing.append((cur_code, lnumbers[cur_code], op, opcode.opname[op], op_arg, etype, extra))
               cur_code += 3
               
     return listing


if __name__ == '__main__':
     
     print repr(disassemble(disassemble.func_code))