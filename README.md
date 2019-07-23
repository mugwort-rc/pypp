pypp
======

boost.python/pybin11/embind generator.

Usage
-----

### Boost.Python

#### Hello world

```
$ cat helloworld.hpp
void helloworld()
{
    std::cout << "Hello World!" << std::endl;
}

$ python -m pypp helloworld.hpp
// generate by pypp
// original source code: helloworld.hpp

#include <boost/python.hpp>

#include "helloworld.hpp"


void init_helloworld_hpp()
{
    boost::python::def("helloworld", &helloworld);
}
```

#### class

```
$ cat class.hpp
class Calc
{
public:
    static int add(int a, int b)
    {
        return a + b;
    }
};

$ python -m pypp class.hpp
// generate by pypp
// original source code: class.hpp

#include <boost/python.hpp>

#include "class.hpp"


void init_class_hpp()
{
    boost::python::class_<Calc>("Calc", boost::python::no_init)
        .def("add", &Calc::add)
        .staticmethod("add")
        ;
}
```

### pybind11

#### Hello world

```
$ cat helloworld.hpp
void helloworld()
{
    std::cout << "Hello World!" << std::endl;
}

$ python -m pypp helloworld.hpp --experimental-pybind11
// generate by pypp
// original source code: helloworld.hpp

#include <pybind11/pybind11.h>

#include "helloworld.hpp"


void init_helloworld_hpp(pybind11::module scope)
{
    scope.def("helloworld", &helloworld);
}
```

#### class

```
$ cat class.hpp
class Calc
{
public:
    static int add(int a, int b)
    {
        return a + b;
    }
};

$ python -m pypp class.hpp --experimental-pybind11
// generate by pypp
// original source code: class.hpp

#include <pybind11/pybind11.h>

#include "class.hpp"


void init_class_hpp(pybind11::module scope) {
    pybind11::class_<Calc, std::shared_ptr<Calc>>(scope, "Calc")
        .def("add", &Calc::add)
        ;
}
```

### Embind

#### Hello world

```
$ cat helloworld.hpp
void helloworld()
{
    std::cout << "Hello World!" << std::endl;
}

$ python -m pypp helloworld.hpp --experimental-embind
// generate by pypp
// original source code: helloworld.hpp

#include <emscripten/bind.h>

#include "helloworld.hpp"


void init_helloworld_hpp()
{
    emscripten::function("helloworld", &helloworld);
}
```

#### class

```
$ cat class.hpp
class Calc
{
public:
    static int add(int a, int b)
    {
        return a + b;
    }
};

$ python -m pypp class.hpp --experimental-embind
// generate by pypp
// original source code: class.hpp

#include <emscripten/bind.h>

#include "class.hpp"


void init_class_hpp() {
    emscripten::class_<Calc>(scope, "Calc")
        .function("add", &Calc::add)
        ;
}
```
