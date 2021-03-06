import tropyc
import nontemplate
import webob
import json

http_server = tropyc.HttpServer("localhost", 8888)
script_manager = tropyc.ScriptManager(http_server)

prime_names = { 2: "The Even Prime", 13: "The Baker's Dozen", 23: "Illuminatus!" }

http_server.addfile("/library.js", "libjs/library.js")

@script_manager.add()
def find_factor(n):
    # All primes are either 2, 3 or 6k +- 1 for k in N
    # This would more elegantly be done with a generator.
    
    if n % 2 == 0: return 2
    if n % 3 == 0: return 3
    
    d = 5
    while d*d <= n:
        if n % d == 0: return d
        d += 2
        if n % d == 0: return d
        d += 4
        
    return None


@script_manager.add()
def check_prime(number):
    factor = find_factor(number)
    if factor is not None:
        alert(number + " is divisible by " + factor )
        return False
    return True

@http_server.rpc()
def submit_prime(name, number):
    number = int(number)
    factor = find_factor(number)
    if factor is not None:
        return { 'error': '%d is divisible by %d' % (number, factor) }
    else:
        prime_names[number] = name


@http_server.url('/')
def show_primes(request):
    D = nontemplate.Document()
    
    with D.html():
        with D.head():
            D.script(_type="text/javascript", src="/library.js")("")
            D.script(_type="text/javascript", src=script_manager.url)("")
        with D.body():
            with D.table():
                with D.tbody():
                    for prime in sorted(prime_names.keys()):
                        with D.tr():
                            D.td()(str(prime))
                            D.td()(prime_names[prime])
            
            with D.form(onSubmit="$Pcheck_prime(this.number.value)", method="post", action="/rpc/submit_prime"):
                D.input(name="number")
                D.input(name="name")
                D.input(_type="submit")
    
    return webob.Response(str(D))

http_server.serve()