// generate by pypp
// original source code: ./samples/helloworld.hpp

#include "./samples/helloworld.hpp"

#include <boost/python.hpp>


void init_samples_helloworld_hpp() {
    boost::python::def("helloworld", &helloworld);
}
