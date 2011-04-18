"""Run some test cases using Rhino to execute the generated Javascript"""
# XXX tests don't actually do anything yet!

import tempfile
import os
import tropyc
import pprint
import dis
import json

def test(func, *argslist):
    
    answers = []
    for args in argslist:
        ans = func(*args)
        if type(ans) in (list, tuple):
            answers.append(",".join( [str(a) if a is not None else 'null' for a in ans] ))
        else:
            answers.append(str(ans) if ans is not None else 'null')
    
    label = func.__name__ + (": " + func.__doc__ if func.__doc__ else "")
    
    try:
        xfunc = tropyc.CodeFunction(func.func_code)
    
        tempfd, tempname = tempfile.mkstemp(suffix=".js")
    
        for jsline in xfunc.jscode():
            os.write(tempfd, jsline + "\n")
    
        for args in argslist:
            os.write(tempfd, "print(%s(%s));\n" % (xfunc.funcname, ",".join([repr(a) for a in args])))
    
        os.close(tempfd)
    
        with os.popen("rhino -f library.js -f %s" % tempname) as rhino_file:
            results = [ rhino_file.readline().strip() for args in argslist ]
    
        os.unlink(tempname)
    
    
        if answers == results:
            print "%-40s PASS" % label
            return
        else:
            print "%-40s FAIL" % label
            pprint.pprint(answers)
            pprint.pprint(results)
            for jsline in xfunc.jscode():
                print jsline
    except Exception, e:
        print "%-40s EXCEPTION %s" % (label, e)
        
    
    dis.dis(func)
    
def t1():
    """Simplest Possible Test!"""
    return 1

test(t1,())


def t1a(a,b,c,d):
    """Order of parameters"""
    return b

test(t1a,(1,2,3,4))

def t2(x,y,z):
    """Parameters and Expressions"""
    return x * y + z

test(t2,(2,3,4))


def t2a(a,b):
    """Some Math"""
    return (a-b,a+b,a*b,a/b)

test(t2a,(4,5),(-1,5),(0,2),(6,1))

def t3(x):
    """A simple loop"""
    i = 2
    t = 1
    while i < x:
        t *= i
        i += 1
    return t

test(t3,(7,))


def t4():
    """List constructor & loop"""
    a = [42,67,128,2,45,1000]
    t = 0
    for n in a:
        t += n
    return t

test(t4,())


def t5(x):
    """If / Elif / Else"""
    if x == 1:
        return 7
    elif x == 2:
        return 8
    else:
        return 9
    
test(t5,(1,),(2,),(3,))


def t6(x):
    """Recursion!"""
    if x > 1:
        return t6(x-1) + t6(x-2)
    else:
        return 1

test(t6,(10,))


def t7(x):
    """Nested Loops"""
    t = 0
    for i in [1,2,3,4,5,6]:
        j = 1
        while j < x:
            for k in [8,9,10]:
                t += i * j * k
            j += 1
    return t

test(t7,(12,),(2,))


def t8(x):
    """List Comprehensions"""
    t = 0
    z = [ x ** y for y in [1,2,3,4]]
    for a in z:
        t += a
    return t

test(t8,(5,))


def t9(a,b,c):
    """Library of builtins"""
    return (min(a,b,c), max(a,b,c))

test(t9,(3,7,4),(1,2,3))

def t9a(a,b):
    """cmp builtins"""
    return cmp(a,b)

test(t9a,(4,5),(9,6),(4,4),("hello","world"))

def t9b(a):
    """sorted builtin"""
    return sorted(a)

test(t9b,([1,2,3,4,5],),([3,9,1,3,4],))

def t10(a):
    """For/Else"""
    for x in [1,2,3,4,5]:
        if x == 3: continue
        if x == a: break
    else:
        x = None
    return x

test(t10,(2,),(4,),(7,))
