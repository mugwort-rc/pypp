// generate by pypp
// original source code: {{ input }}

#include "{{ input }}"{% for name in class_forward_declarations %}
// TODO: forward declaration class {{ name }}{% endfor %}

#include <boost/python.hpp>
{% if install_defvisitor %}
{% for name in def_visitors %}
#include "{{ name }}.hpp"{% endfor %}
{% endif %}
{% if has_decls %}
{{ decl_code }}
{% endif %}
void init_{{ snake_input }}() {
{{ generated }}
}
