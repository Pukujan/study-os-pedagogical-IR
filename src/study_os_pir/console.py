from __future__ import annotations

from .runtime import RendererTurnContract
from .vertical import VerticalRepresentation


def render_representation_text(representation: VerticalRepresentation) -> str:
    label_width = max(len(row.label) for row in representation.rows)
    lines = [
        f"{row.label:<{label_width}}: " + " ".join(f"{value:>5}" for value in row.values)
        for row in representation.rows
    ]
    if representation.box is not None:
        value_count = max(len(row.values) for row in representation.rows)
        end = representation.box.start_index + representation.box.width
        markers = [
            "^^^^^" if representation.box.start_index <= index < end else "     "
            for index in range(value_count)
        ]
        lines.append(f"{'box':<{label_width}}: " + " ".join(markers))
    lines.extend(f"{'':<{label_width}}  {note}" for note in representation.annotations)
    return "\n".join(lines)


def render_turn_text(contract: RendererTurnContract) -> str:
    lines = [render_representation_text(contract.representation)]
    if contract.probe is not None:
        lines.extend(["", contract.probe.prompt])
    return "\n".join(lines)
