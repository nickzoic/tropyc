/* Python Builtins not implemented yet ... some of these never will be,
obviously.
XXX Need to work out some way to throw a NotImplementedError in those cases

XXX This can get replaced with the existing libraries from elsewhere.

			  	input() 	open() 	        staticmethod()
all()			 	 	        ord() 	        
any() 	        eval() 	        isinstance() 	 	        sum()
basestring() 	execfile() 	issubclass() 	print() 	super()
file() 	                        iter() 	        property() 	tuple()
	        filter() 	 	                        type()
bytearray() 		 	list() 	        raw_input() 	unichr()
callable() 	format() 	locals() 	     		unicode()
chr() 	        frozenset() 		        reload() 	vars()
classmethod() 	getattr() 	map() 	        repr() 	        
globals() 	                 	        reversed() 	
compile() 	hasattr() 	memoryview() 	round() 	__import__()
complex() 	hash() 	         	        set() 	        apply()
delattr() 	help() 	        next() 	        setattr() 	buffer()
dict()                          object() 	slice() 	coerce()
dir() 	        id() 	         	                        intern()

*/

$Pabs = Math.abs;

function $Pbin(n) { return parseInt(n,10).toString(2); }

function $Pbool(x) { return !!x; }

function $Pcmp(a,b) { return (a < b) ? -1 : ((a > b) ? +1 : 0) }

function $Pdivmod(a,b) { m = a % b; return [ (a-m) / b, m ]; }

// XXX again, should be a generator
function $Penumerate(x,s) {
    var ll = [];
    s = s || 0;
    for (var i in x) {
       ll.push([i*1+s, x[i]]);
    }
    return ll;
}

function $Pfloat(x) { return x * 1; }

function $Phex(n) { return parseInt(n,10).toString(16); }

$Pint = Math.floor;

function $Plen(x) { return x.length; }

function $Plong(x) { return x * 1; }

$Pmax = Math.max;

$Pmin = Math.min;

function $Poct(n) { return parseInt(n,10).toString(8); }

function $Ppow(x,y,z) { if (z) { return pow(x,y) % z; } else { return pow(x,y); } }

function $Prange() {
    var start = 0, stop, step = 1;
    if (arguments.length == 1) { stop = arguments[0]; }
    else { start = arguments[0]; stop = arguments[1]; step = arguments[2] || 1; }
    var ll = [];
    for (var x = start; x < stop; x += step) { ll.push(x); }
    return ll;
}

function $Preduce(func, seq, val) {
    var i = 0;    
    if (arguments.length == 2) {
	val = seq[0];
	i = 1;
    }
    while (i < seq.length) {
        val = func(val, seq[i]);
    }
    return val;
}

function $Psorted(a) { var b = a.slice(); b.sort(); return b; }

function $Pstr(n) { return n.toString(); }

// XXX Should really definitely be a generator instead.
$Pxrange = $Prange;

function $Pzip() {
    var ll = [];
    var i = 0;
    while(1) {
        var x = [];
        for (var j=0; j < arguments.length; j++) {
	    if (i >= arguments[j].length) { return ll; } 
	    x.push(arguments[j][i]);
	}
	ll.push(x);
	i++;
    }
}

$PTrue = true;
$PFalse = false;
$Palert = alert;