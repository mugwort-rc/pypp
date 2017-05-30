// generate by pypp
// original source code: ./samples/noncopyable.hpp

#include "./samples/noncopyable.hpp"

#include <boost/python.hpp>

void init_samples_noncopyable_hpp() {
    boost::python::class_<Noncopyable, std::shared_ptr<Noncopyable>, boost::noncopyable>("Noncopyable", boost::python::no_init)
        ;
}
