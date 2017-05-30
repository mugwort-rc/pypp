// generate by pypp
// original source code: ./samples/enum.hpp

#include "./samples/enum.hpp"

#include <boost/python.hpp>

void init_samples_enum_hpp() {
    boost::python::enum_<Enum>("Enum")
        .value("A", A)
        .value("B", B)
        .value("C", C)
        .export_values()
        ;
    boost::python::enum_<Enum_t>("Enum_t")
        .value("X", X)
        .value("Y", Y)
        .value("Z", Z)
        .export_values()
        ;
}
