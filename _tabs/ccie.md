---
layout: page
icon: fas fa-award
order: 3
title: CCIE
toc: false
---

Study notes for the **CCIE Data Center v3.1** lab exam, organized by the
seven domains of the 8-hour lab blueprint. The written qualifying exam is
the same 350-601 DCCOR covered under [CCNP](/ccnp/).

<ul>
{% assign notes = site.ccie | sort: "order" %}
{% for note in notes %}
  <li style="margin-bottom: 0.6rem;">
    <a href="{{ note.url | relative_url }}"><strong>{{ note.title }}</strong></a>
    {% if note.weight %}<span class="text-muted"> — {{ note.weight }} of the exam</span>{% endif %}
    {% if note.description %}<br><span class="text-muted">{{ note.description }}</span>{% endif %}
  </li>
{% endfor %}
</ul>
