"""Run some test cases using Rhino to execute the generated Javascript"""

import tempfile
import os
import tropyc
import pprint
import dis
import json

def test(func, *argslist):
    
    # send answers to JSON and back to get them into a standard form.
    answers = json.loads(json.dumps([ func(*args) for args in argslist ]))
    
    label = func.__name__ + (": " + func.__doc__ if func.__doc__ else "")
    
    try:
        jscode = tropyc.transform_js(func, debug=True)
    
        tempfd, tempname = tempfile.mkstemp(prefix="tropyc", suffix=".js")
        os.write(tempfd, jscode);
        callfunc = ",".join(["$P%s(%s)" % (func.__name__, json.dumps(args)[1:-1]) for args in argslist])
        os.write(tempfd, "\nprint(JSON.stringify([%s]));\n" % callfunc)
        os.close(tempfd)
    
        rhino_file = os.popen("rhino -f libjs/json2.js -f libjs/library.js -f %s" % tempname)
        results = json.load(rhino_file)
        rhino_file.close()
        
        os.unlink(tempname)
    
        if answers == results:
            print "%-40s PASS" % label
            return
        else:
            print "%-40s FAIL" % label
            pprint.pprint(answers)
            pprint.pprint(results)
            print jscode
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

def t2(v,w,x,y,z):
    """Parameters and Expressions"""
    return (v + w) * x + y * z

test(t2,(2,3,4,5,6))


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
