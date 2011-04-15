"""Run some test cases using Rhino to execute the generated Javascript"""
# XXX tests don't actually do anything yet!

import tempfile
import os
import tropyc
import pprint

def test(func, *argslist):
    
    answers = [ str(func(*args)) for args in argslist ]

    xfunc = tropyc.CodeFunction(func.func_code)
    
    tempfd, tempname = tempfile.mkstemp(suffix=".js")
    
    for jsline in xfunc.jscode():
        os.write(tempfd, jsline + "\n")
    
    for args in argslist:
        os.write(tempfd, "print(%s(%s));\n" % (xfunc.funcname, ",".join([repr(a) for a in args])))
    
    os.close(tempfd)
    
    with os.popen("rhino -f %s" % tempname) as rhino_file:
        results = [ rhino_file.readline().strip() for args in argslist ]
    
    label = func.__name__ + (": " + func.__doc__ if func.__doc__ else "")
    
    if answers == results:
        print "%-40s PASS" % label
        os.unlink(tempname)
    else:
        print "%-40s FAIL" % label
        pprint.pprint(answers)
        pprint.pprint(results)
        for jsline in xfunc.jscode():
            print jsline
        
    
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
    
test(e,(1,),(2,),(3,))


def f(x):
    """Recursion!"""
    if x > 1:
        return f(x-1) + f(x-2)
    else:
        return 1

test(f,(10,))


def g(x):
    """Nested Loops"""
    t = 0
    for i in [1,2,3,4,5,6]:
        j = 1
        while j < x:
            for k in [8,9,10]:
                t += i * j * k
            j += 1
    return t

test(g,(12,),(2,))


def h(x):
    """List Comprehensions"""
    t = 0
    z = [ x ** y for y in [1,2,3,4]]
    for a in z:
        t += a
    return t

test(h,(5,))