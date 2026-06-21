"""Even Brief - automated daily news briefing generator and static-site builder.

The package is split into two halves that meet at a validated data contract
(``schema.py``):

* the **generation** backend (``client``, ``discover``, ``research``, ``write``,
  ``verify``, ``markets``, ``weather``, ``images``, ``assemble``, ``pipeline``)
  researches the day's news via the Anthropic API and produces a validated
  ``Edition``; and
* the **build** step (``build/render.py``) renders an ``Edition`` through the
  Jinja templates into the self-contained ``index.html`` plus ``archive.json``.

See ARCHITECTURE.md for how the pieces fit together.
"""

__version__ = "1.0.0"
