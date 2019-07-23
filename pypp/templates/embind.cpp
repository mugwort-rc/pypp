// generate by pypp
// original source code: {{ input }}

#include <emscripten/bind.h>

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
void init_{{ init_name }}() {
{{ generated }}
}
