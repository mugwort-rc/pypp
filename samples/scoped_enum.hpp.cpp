// generate by pypp
// original source code: ./samples/scoped_enum.hpp

#include <boost/python.hpp>
#include "./samples/scoped_enum.hpp"

void init_samples_scoped_enum_hpp() {
    auto boost_python_Class = boost::python::class_<Class>("Class", boost::python::no_init)
        ;
    {
        boost::python::scope scope = boost_python_Class;
        boost::python::enum_<Enum>("Enum")
            .value("A", &A)
            .value("B", &B)
            .value("C", &C)
            .export_values()
            ;
    }
}
