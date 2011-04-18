/* builtins

abs() 	divmod() 	input() 	open() 	staticmethod()
all() 	enumerate() 	int() 	ord() 	str()
any() 	eval() 	isinstance() 	pow() 	sum()
basestring() 	execfile() 	issubclass() 	print() 	super()
bin() 	file() 	iter() 	property() 	tuple()
bool() 	filter() 	len() 	range() 	type()
bytearray() 	float() 	list() 	raw_input() 	unichr()
callable() 	format() 	locals() 	reduce() 	unicode()
chr() 	frozenset() 	long() 	reload() 	vars()
classmethod() 	getattr() 	map() 	repr() 	xrange()
cmp() 	globals() 	max() 	reversed() 	zip()
compile() 	hasattr() 	memoryview() 	round() 	__import__()
complex() 	hash() 	min() 	set() 	apply()
delattr() 	help() 	next() 	setattr() 	buffer()
dict() 	hex() 	object() 	slice() 	coerce()
dir() 	id() 	oct() 	sorted() 	intern()

*/

$Pabs = Math.abs;

function $Pbin(n) { return parseInt(n,10).toString(2); }

function $Pcmp(a,b) { return (a < b) ? -1 : ((a > b) ? +1 : 0) }

function $Phex(n) { return parseInt(n,10).toString(16); }

$Pint = Math.floor;

$Pmax = Math.max;

$Pmin = Math.min;

function $Poct(n) { return parseInt(n,10).toString(8); }

function $Psorted(a) { var b = a.slice(); b.sort(); return b; }

function $Pstr(n) { return n.toString(); }
