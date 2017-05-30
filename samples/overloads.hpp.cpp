// generate by pypp
// original source code: ./samples/overloads.hpp

#include "./samples/overloads.hpp"

#include <boost/python.hpp>


BOOST_PYTHON_FUNCTION_OVERLOADS(addOverloads0, add, 1, 2)

void init_samples_overloads_hpp() {
    boost::python::def("add", static_cast<int(*)(int, int)>(&add), addOverloads0());
    boost::python::def("add", static_cast<double(*)(double, double)>(&add));
}
