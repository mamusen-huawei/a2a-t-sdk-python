# Prompt rendering

The sectioned template renderer implements the section grammar shared by every A2A-T template: a template is split into `## ` title sections, and a section whose first non-blank body line is a slot placeholder is a slot section.

The two blank-slot policies are deliberately two separate functions and are not interchangeable (port decision D12): the collapse policy keeps the section scaffolding of the template, while the drop policy removes a blank slot section entirely. The task prompt pipeline renders through the collapse policy; the negotiation content layer renders through the drop policy, because a negotiation message must not show empty section headings for information the counterparty did not provide.

::: a2a_t.prompt.task_rendering.sectioned_renderer

## Rendering failure

The collapse policy rejects malformed template content (unbalanced braces, an unknown double-braced slot) with a catalog-coded failure; the drop policy substitutes leniently and never fails on template content.

::: a2a_t.prompt.task_rendering.errors
