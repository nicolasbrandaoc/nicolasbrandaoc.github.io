---
layout: page
icon: fas fa-graduation-cap
order: 1
title: CCNA
toc: false
---

Study notes for the **Cisco CCNA 200-301** exam, organized by the six official
exam domains. Each page is a living summary I update as I go through the
blueprint.

<ul>
{% assign ccna_notes = site.ccna | sort: "order" %}
{% for note in ccna_notes %}
  <li style="margin-bottom: 0.6rem;">
    <a href="{{ note.url | relative_url }}"><strong>{{ note.title }}</strong></a>
    {% if note.weight %}<span class="text-muted"> — {{ note.weight }} of the exam</span>{% endif %}
    {% if note.description %}<br><span class="text-muted">{{ note.description }}</span>{% endif %}
  </li>
{% endfor %}
</ul>
