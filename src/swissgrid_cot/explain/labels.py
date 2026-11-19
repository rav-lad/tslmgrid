"""The label of a day: its calendar context, by explicit ordered rules. No model, no LLM.

First matching rule wins, in the order of ``annotate.causes``:

  1. lockdown          the 2020 lockdown (16 Mar - 10 May 2020)
  2. christmas_period  22 Dec - 6 Jan (Christmas school holidays), weekends included
  3. public_holiday    Monday-Friday, holiday for at least 20 % of the population
  4. bridge_day        Monday before a Tuesday holiday / Friday after a Thursday holiday
  5. summer_holidays   14 Jul - 15 Aug (overlap of the cantonal summer school holidays), weekends included
  6. ordinary

A holiday on a weekend day is an ordinary weekend day (``review.context.kind_of``). A seventh label,
``irregularity``, marks a simulated sample: an ordinary day with a deviation added to a few hours.
"""

LABELS = (
    "ordinary",
    "public_holiday",
    "bridge_day",
    "christmas_period",
    "summer_holidays",
    "lockdown",
    "irregularity",
)
CALENDAR_LABELS = LABELS[1:6]
SIGNATURE = {
    "ordinary": "The day follows an ordinary day of its type: no calendar effect.",
    "public_holiday": "A working day that loses its working-day level and moves toward a Sunday is the signature "
                      "of a public holiday.",
    "bridge_day": "A working day that keeps its working-day shape at a lower level, with part of the activity "
                  "missing, is the signature of a bridge day between a holiday and the weekend.",
    "christmas_period": "A day held below its ordinary level over most hours, with a flattened shape, is the "
                        "signature of the Christmas holidays.",
    "summer_holidays": "A day with its usual shape, held slightly below an ordinary day of its type, is the "
                       "signature of the summer holiday weeks.",
    "lockdown": "A deep cut of the whole day, strongest in the working hours, is the signature of the lockdown.",
    "irregularity": "A gap confined to a few hours while the rest of the day follows an ordinary day is a local "
                    "irregularity (an event, an outage or a metering problem), not a calendar effect.",
}  # fmt: skip
CAUSE_OF_LABEL = {
    "public_holiday": "public_holiday",
    "bridge_day": "bridge_day",
    "christmas_period": "christmas_newyear",
    "summer_holidays": "summer_holidays",
    "lockdown": "covid_lockdown",
}
"""The cause ``annotate.causes`` gives a flagged day with that calendar label."""


def label_of(kind: str, period: str) -> str:
    """The label of a day from its calendar kind and period (``review.context.kind_of``, ``period_of``)."""
    if kind == "lockdown":
        return "lockdown"
    if period == "christmas":
        return "christmas_period"
    if kind in ("full_holiday", "partial_holiday"):
        return "public_holiday"
    if kind == "bridge_day":
        return "bridge_day"
    if period == "summer":
        return "summer_holidays"
    return "ordinary"
