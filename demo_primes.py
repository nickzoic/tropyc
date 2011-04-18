import tropyc

http_server = tropyc.http_server(localhost, 8000)
script_manager = tropyc.script_manager(http_server)

prime_names = { 2: "The Even Prime", 13: "The Baker's Dozen", 23: "Illuminatus!" }

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
        alert("%d is divisible by %d" % (number, factor) )
        return True
    return False

@http_server.rpc()
def submit_prime(name, number):
    factor = find_factor(number)
    if factor is not None:
        return { 'error': '%d is divisible by %d' % (number, factor) }
    else:
        prime_names[number] = name
    
@http_server.url('/')
def show_primes():
    D = nontemplate.document()
    
    with D.html:
        with D.head:
            D.script(url=script_manager.url)
        with D.body:
            with D.table():
                with D.tbody():
                    for prime in sorted(prime_names.keys()):
                        D.tr(D.td(prime), D.td(prime_names[prime]))
            
            with D.form(method="post", action=submit_prime, onsubmit=check_prime):
                D.input(name="name")
                D.input(name="number")

