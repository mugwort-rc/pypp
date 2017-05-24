#ifndef PYPP_GENERATED_{{ class_name | upper }}_DEFVISITOR_HPP
#define PYPP_GENERATED_{{ class_name | upper }}_DEFVISITOR_HPP

class {{ class_name }}DefVisitor :
    public boost::python::def_visitor<{{ class_name }}DefVisitor>
{
    friend class def_visitor_access;
public:
    template <class T>
    void visit(T &class_) const {
        class_
            .def("example", &example)
            ;
    }

    static void example({{ class_name }} &self) {
        // something to do
    }

};

#endif  // PYPP_GENERATED_{{ class_name | upper }}_DEFVISITOR_HPP
