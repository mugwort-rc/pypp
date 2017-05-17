pypp
======

boost.python generator.

Usage
-----

### Hello world

```
$ cat helloworld.hpp
void helloworld()
{
    std::cout << "Hello World!" << std::endl;
}

$ python -m pypp helloworld.hpp
// generate by pypp
// original source code: helloworld.hpp
void init_helloworld_hpp()
{
    boost::python::def("helloworld", &helloworld);
}
```

### class

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
void init_class_hpp()
{
    boost::python::class_<Calc>("Calc", boost::python::no_init)
        .def("add", &Calc::add)
        .staticmethod("add")
        ;
}
```
