from __future__ import annotations

from .runtime import RendererTurnContract
from .vertical import VerticalRepresentation, VerticalWindowBox


def _window_boxes(representation: VerticalRepresentation) -> tuple[VerticalWindowBox, ...]:
    legacy = () if representation.box is None else (representation.box,)
    return (*legacy, *representation.boxes)


def render_representation_text(representation: VerticalRepresentation) -> str:
    boxes = _window_boxes(representation)
    label_width = max(
        *(len(row.label) for row in representation.rows),
        *(len(box.label) for box in boxes),
    )
    lines = [
        f"{row.label:<{label_width}}: " + " ".join(f"{value:>5}" for value in row.values)
        for row in representation.rows
    ]
    value_count = max(len(row.values) for row in representation.rows)
    for box in boxes:
        end = box.start_index + box.width
        markers = [
            "^^^^^" if box.start_index <= index < end else "     "
            for index in range(value_count)
        ]
        lines.append(f"{box.label:<{label_width}}: " + " ".join(markers))
    lines.extend(f"{'':<{label_width}}  {note}" for note in representation.annotations)
    return "\n".join(lines)


def render_turn_text(contract: RendererTurnContract) -> str:
    lines: list[str] = []
    if contract.persistent_text:
        lines.extend([*contract.persistent_text, ""])
    lines.append(render_representation_text(contract.representation))
    if contract.probe is not None:
        lines.extend(["", contract.probe.prompt])
    return "\n".join(lines)
