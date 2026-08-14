"""Structured queries over the 2014 NMIS health facility survey."""
import pandas as pd

SURVEY_CAVEAT = ("(Based on the 2014 national health facility survey — "
                 "facilities may have changed since. Confirm locally.)")


def summarize_area(df: pd.DataFrame, state: str, lga: str | None = None) -> str | None:
    sub = df[df["state"].str.lower() == state.lower()]
    if lga:
        sub = sub[sub["lga"].str.lower() == lga.lower()]
    if sub.empty:
        return None

    n = len(sub)
    types = sub["facility_type_display"].value_counts().head(3)
    type_str = ", ".join(f"{count} {name}" for name, count in types.items())
    with_doctor = (sub["num_doctors_fulltime"] > 0).sum()
    public = (sub["management"] == "public").sum()

    area = f"{lga} LGA, {state}" if lga else f"{state} State"
    return (
        f"The survey covered {n} health facilities in {area}: {type_str}. "
        f"{public} are publicly managed, and {with_doctor} had at least one "
        f"full-time doctor at survey time. {SURVEY_CAVEAT}"
    )