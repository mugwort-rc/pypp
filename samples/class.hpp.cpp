// generate by pypp
// original source code: ./samples/class.hpp
void init_samples_class_hpp() {
    boost::python::class_<Calc>("Calc", boost::python::no_init)
        .def("add", &Calc::add)
        .staticmethod("add")
        ;
}
