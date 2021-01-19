pypp
======

pybin11 / boost.python / embind generator.

Usage
-----

## Config

### Ubuntu 18.04

```
$ cat .PYPP_LIBCLANG_PATH
[llvm]
# Ubuntu 20.04
libclang=/usr/lib/llvm-10/lib/libclang.so
```

### pybind11

#### Hello world

```
$ cat samples/helloworld.hpp
void helloworld()
{
    std::cout << "Hello World!" << std::endl;
}

$ python -m pypp samples/helloworld.hpp
// generate by pypp
// original source code: samples/helloworld.hpp

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "samples/helloworld.hpp"


void init_samples_helloworld_hpp(pybind11::module scope) {
    scope.def("helloworld", &helloworld);
}

```

#### class

```
$ cat samples/class.hpp
class Calc
{
public:
    static int add(int a, int b)
    {
        return a + b;
    }
};

$ python -m pypp samples/class.hpp
// generate by pypp
// original source code: samples/class.hpp

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "samples/class.hpp"


void init_samples_class_hpp(pybind11::module scope) {
    pybind11::class_<Calc, std::shared_ptr<Calc>>(scope, "Calc")
        .def_static("add", &Calc::add)
        ;
}
```

### Boost.Python

#### Hello world

```
$ python -m pypp samples/helloworld.hpp --generate-boost
// generate by pypp
// original source code: samples/helloworld.hpp

#include <boost/python.hpp>

#include "samples/helloworld.hpp"


void init_samples_helloworld_hpp()
{
    boost::python::def("helloworld", &helloworld);
}
```

#### class

```
$ python -m pypp samples/class.hpp --generate-boost
// generate by pypp
// original source code: class.hpp

#include <boost/python.hpp>

#include "samples/class.hpp"


void init_samples_class_hpp()
{
    boost::python::class_<Calc>("Calc", boost::python::no_init)
        .def("add", &Calc::add)
        .staticmethod("add")
        ;
}
```

### Embind

#### Hello world

```
$ python -m pypp samples/helloworld.hpp --generate-embind
// generate by pypp
// original source code: samples/helloworld.hpp

#include <emscripten/bind.h>

#include "samples/helloworld.hpp"


void init_samples_helloworld_hpp()
{
    emscripten::function("helloworld", &helloworld);
}
```

#### class

```
$ python -m pypp class.hpp --generate-embind
// generate by pypp
// original source code: samples/class.hpp

#include <emscripten/bind.h>

#include "samples/class.hpp"


void init_samples_class_hpp() {
    emscripten::class_<Calc>(scope, "Calc")
        .function("add", &Calc::add)
        ;
}
```
