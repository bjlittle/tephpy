{% for section, _ in sections.items() %}
{% for category, val in definitions.items() if category in sections[section] %}
{{ definitions[category]['name'] }}
{{ "^" * definitions[category]['name']|length }}

{% for text, values in sections[section][category].items() %}
- {{ text }} ({{ values|join(', ') }})
{% endfor %}

{% endfor %}
{% endfor %}