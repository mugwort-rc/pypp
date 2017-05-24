// generate by pypp
// original source code: ./samples/virtual_method.hpp

#include <boost/python.hpp>
#include "./samples/virtual_method.hpp"


class VirtualMethodWrapper :
    public VirtualMethod,
    public boost::python::wrapper<VirtualMethod>
{
public:
    void v (int hoge) {
        if ( auto v = this->get_override("v") ) {
            v(hoge);
        } else {
            VirtualMethod::v(hoge);
        }
    }
    int p (int x, int y) const {
        return this->get_override("p")(x, y);
    }
};


void init_samples_virtual_method_hpp() {
    boost::python::class_<VirtualMethodWrapper>("VirtualMethod", boost::python::no_init)
        .def("v", &VirtualMethod::v)
        .def("p", boost::python::pure_virtual(&VirtualMethod::p))
        ;
}
