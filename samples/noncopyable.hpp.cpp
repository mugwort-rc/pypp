// generate by pypp
// original source code: ./samples/noncopyable.hpp
void init_samples_noncopyable_hpp() {
    boost::python::class_<Noncopyable, boost::noncopyable>("Noncopyable", boost::python::no_init)
        ;
}
