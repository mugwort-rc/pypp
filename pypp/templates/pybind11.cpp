// generate by pypp
// original source code: {{ input }}

#include <pybind11/pybind11.h>

#include "{{ input }}"{% for name in class_forward_declarations %}
// TODO: forward declaration class {{ name }}{% endfor %}

{% if install_defvisitor %}
{% for name in def_visitors %}
#include "{{ name }}.hpp"{% endfor %}
{% endif %}
{% if has_decls %}
{{ decl_code }}
{% endif %}
void init_{{ init_name }}(pybind11::handle scope) {
{{ generated }}
}
