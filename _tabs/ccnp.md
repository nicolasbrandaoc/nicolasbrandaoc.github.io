---
layout: page
icon: fas fa-certificate
order: 2
title: CCNP
toc: false
---

Study notes for the **CCNP Data Center** track, built around the
**350-601 DCCOR** core exam and organized by its five official domains.

<ul>
{% assign notes = site.ccnp | sort: "order" %}
{% for note in notes %}
  <li style="margin-bottom: 0.6rem;">
    <a href="{{ note.url | relative_url }}"><strong>{{ note.title }}</strong></a>
    {% if note.weight %}<span class="text-muted"> — {{ note.weight }} of the exam</span>{% endif %}
    {% if note.description %}<br><span class="text-muted">{{ note.description }}</span>{% endif %}
  </li>
{% endfor %}
</ul>
