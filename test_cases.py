import tempfile
import os
#import tropyc

def test(func, *args):
    answer = func(*args)

    #xfunc = tropyc.transform(func)
    
    tempfd, tempname = tempfile.mkstemp(suffix=".js")
    #os.write(tempfd, xfunc.jscode)
    #os.write(tempfd, "\nprint(%s(%s));\n" % (xfunc.name, ",".join(repr(a) for a in args)))
    os.write(tempfd, 'print("Hello, World!");')
    os.close(tempfd)
    
    rhino = os.popen("rhino -f "+tempname)
    result = rhino.read()
    rhino.close()
    
    os.unlink(tempname)

    print "%10s %40s %s %s" % (func.__name__, func.__doc__, answer, result)
    
def a():
    """Simplest Possible Test!"""
    return 1

test(a)

def b(x,y,z):
    """Parameters and Expressions"""
    return x * y + z

test(b,2,3,4)

def c(x):
    """A simple loop"""
    i = 2
    t = 1
    while i < x:
        t *= i
        i += 1
    return t

test(c,7)

def d():
    """List constructor & loop"""
    a = [42,67,128,2,45]
    t = 0
    for n in a:
        t += n
    return t

test(d)