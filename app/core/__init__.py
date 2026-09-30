"""Cross-cutting infrastructure: logging and the application error boundary.

`app.core` carries no business logic and no exchange knowledge. Modules here
must stay importable by every other layer, so they depend on nothing inside the
project except each other.
"""
