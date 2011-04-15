"""Run some test cases using Rhino to execute the generated Javascript"""
# XXX tests don't actually do anything yet!

import tempfile
import os
import tropyc

def test(func, args):
    answer = func(*args)

    xfunc = tropyc.CodeFunction(func.func_code)
    
    tempfd, tempname = tempfile.mkstemp(suffix=".js")
    
    for jsline in xfunc.jscode():
        os.write(tempfd, jsline + "\n")
        
    os.write(tempfd, "print(%s(%s));\n" % (xfunc.funcname, ",".join([repr(a) for a in args])))
    
    #os.write(tempfd, 'print("%s");' % answer)
    os.close(tempfd)
    
    rhino = os.popen("rhino -f %s" % tempname)
    result = rhino.read()
    rhino.close()
    
    #os.unlink(tempname)

    label = func.__name__ + (": " + func.__doc__ if func.__doc__ else "")
    status = "PASS" if str(answer).strip() == str(result).strip() else "FAIL"
    print "%-40s %s" % (label, status)
    
def a():
    """Simplest Possible Test!"""
    return 1

test(a,())

def b(x,y,z):
    """Parameters and Expressions"""
    return x * y + z

test(b,(2,3,4))


def c(x):
    """A simple loop"""
    i = 2
    t = 1
    while i < x:
        t *= i
        i += 1
    return t

test(c,(7,))

def d():
    """List constructor & loop"""
    a = [42,67,128,2,45,1000]
    t = 0
    for n in a:
        t += n
    return t

test(d,())

def e(x):
    """If / Elif / Else"""
    if x == 1:
        return 7
    elif x == 2:
        return 8
    else:
        return 9
    
test(e,(1,))
test(e,(2,))
test(e,(3,))

def f(x):
    """Recursion!"""
    if x > 1:
        return f(x-1) + f(x-2)
    else:
        return 1

test(f,(10,))