// generate by pypp
// original source code: {{ input }}

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "{{ input }}"{% for name in class_forward_declarations %}
// TODO: forward declaration class {{ name }}{% endfor %}

{% if install_common_h %}
#include "{{ common_h }}"{% endif %}

{% if install_defvisitor %}
{% for name in def_visitors %}
#include "{{ name }}.hpp"{% endfor %}
{% endif %}
{% if has_decls %}
{{ decl_code }}
{% endif %}
void init_{{ init_name }}(pybind11::module scope) {
{{ generated }}
}
