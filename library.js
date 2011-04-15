$Pmin = function (ns) {
    var m = ns[0];
    for (var i=1; i<ns.length; i++) {
        if (ns[i] < m) {
            m = ns[i];
        }
    }
    return m;
}

$Pmax = function (ns) {
    var m = ns[0];
    for (var i=1; i<ns.length; i++) {
        if (ns[i] > m) {
            m = ns[i];
        }
    }
    return m;
}
