// generate by pypp
// original source code: ./samples/scoped_enum.hpp

#include "./samples/scoped_enum.hpp"

#include <boost/python.hpp>


void init_samples_scoped_enum_hpp() {
    auto boost_python_Class = boost::python::class_<Class, std::shared_ptr<Class>, boost::noncopyable>("Class", boost::python::no_init)
        ;
    {
        boost::python::scope scope = boost_python_Class;
        boost::python::enum_<Class::Enum>("Enum")
            .value("A", Class::A)
            .value("B", Class::B)
            .value("C", Class::C)
            .export_values()
            ;
    }
}
