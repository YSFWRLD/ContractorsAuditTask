"""Structured pricing trace: every number the engine produces can be walked back to a clause."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TraceStep:
    rule: str                          # short machine name, e.g. "zone_factor"
    source: str                        # clause / schedule / page relied on
    calculation: str                   # human-readable arithmetic or decision
    result: str                        # value after this step (as printed Decimal)
    inputs: dict[str, str] = field(default_factory=dict)
    interpretation: str | None = None  # "switch=value" when a CivilWorksInterpretation choice decided the step

    def as_dict(self) -> dict:
        return {"rule": self.rule, "source": self.source, "inputs": self.inputs, "calculation": self.calculation,
                "result": self.result, "interpretation": self.interpretation}
