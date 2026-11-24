"""G2: AWS on-demand list price per GPU-hour for fixed instance types (docs/kallor/g1g2_nya.md)."""

from __future__ import annotations

from functools import partial

from ai_tracker.catalog import Spec
from ai_tracker.sources import aws_gpu

_NOTE = ("Senaste prislista publicerad ≤ månadsslut (versionens id = publiceringstid); known_from = månadsslut + 1. "
         "On-demand, Linux, delad tenancy, us-east-1, delat med antal GPU:er. Listpris, inte marknadspris. "
         "Se docs/kallor/g1g2_nya.md")

SPECS = [
    Spec(key="g2_aws_a100_gpu_hour", branch="G2", label="AWS: listpris per A100-timme (p4d.24xlarge / 8)",
         unit="USD per GPU-timme", freq="M", source="AWS Price List (AmazonEC2, arkiverade versioner)",
         fetch=partial(aws_gpu.price_series, "p4d.24xlarge"), lag_days=1, license=aws_gpu.LICENSE,
         revised=False, publish=False, question="Vad kostar en fast GPU-generation att hyra över tid?", note=_NOTE),
    Spec(key="g2_aws_h100_gpu_hour", branch="G2", label="AWS: listpris per H100-timme (p5.48xlarge / 8)",
         unit="USD per GPU-timme", freq="M", source="AWS Price List (AmazonEC2, arkiverade versioner)",
         fetch=partial(aws_gpu.price_series, "p5.48xlarge"), lag_days=1, license=aws_gpu.LICENSE,
         revised=False, publish=False, question="Vad kostar en H100 att hyra över tid?", note=_NOTE),
]
