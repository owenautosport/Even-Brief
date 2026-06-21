"""Weather section for Guildford, UK.

Builds the masthead widget, current strip, Met Office / UKHSA warnings, today's
24-hour temperature + precipitation arrays, the 7-day forecast, and sources.
Real sourced data (Met Office) only.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from .schema import (
    MastheadWeather,
    Source,
    WarnCard,
    Weather,
    WeatherDay,
)

if TYPE_CHECKING:
    from .client import BriefingClient


# --------------------------------------------------------------------------- #
# Parse targets
# --------------------------------------------------------------------------- #
class _Warn(BaseModel):
    sev: str                 # amber|yellow|red|none
    sev_label: str
    title: str
    body_html: str


class _Day(BaseModel):
    d: str                   # "Sun 21"
    ic: str                  # emoji
    cond: str
    hi: int
    lo: int
    feels: int
    wind: int
    gust: int
    hum: int
    uv: int
    pc: int                  # precip chance %
    mm: float                # precip mm
    sr: str                  # sunrise
    ss: str                  # sunset
    warn: bool = False
    tag: str
    sum: str


class _SourceNote(BaseModel):
    outlet: str
    title: str
    url: str


class _WeatherData(BaseModel):
    masthead_temp: str       # "25°C"
    masthead_cond: str
    masthead_low: str        # "↓ Low 17°C"
    masthead_rain: str       # "Rain <5%"
    masthead_gusts: str      # "Gusts 24 mph"
    current_temp: str
    current_cond: str
    current_meta: str
    warnings: list[_Warn] = Field(default_factory=list)
    hourly_temp: list[int] = Field(min_length=24, max_length=24)
    hourly_precip: list[int] = Field(min_length=24, max_length=24)
    days: list[_Day] = Field(min_length=1)
    sources: list[_SourceNote] = Field(min_length=1)


_SYSTEM = (
    "You are a weather desk writer for 'Even Brief'. Neutral register. Use only "
    "real, sourced data from the Met Office (and UKHSA for health alerts). Do not "
    "invent figures. The location is Guildford, Surrey, UK."
)

_VALID_SEV = {"amber", "yellow", "red", "none"}


def build_weather(client: "BriefingClient") -> Weather:
    """Research and assemble the Guildford weather payload."""
    prompt = (
        "Research today's weather for Guildford, Surrey, UK from the Met Office "
        "(metoffice.gov.uk) and gather:\n"
        "- a masthead summary: current temp, conditions, low, rain chance, gusts;\n"
        "- a current strip: big temperature, conditions, and a feels-like/low meta "
        "line;\n"
        "- any Met Office weather warnings or UKHSA heat/cold alerts covering "
        "Surrey / SE England (severity amber/yellow/red, label, title, body);\n"
        "- today's HOURLY temperature for 00:00-23:00 as 24 integers (Celsius);\n"
        "- today's HOURLY precipitation chance for 00:00-23:00 as 24 integers (%);\n"
        "- a 7-DAY forecast: per day give label (e.g. 'Sun 21'), emoji icon, "
        "condition, high, low, feels-like, wind, gust, humidity, UV, precip chance, "
        "precip mm, sunrise, sunset, a warn flag, a short tile tag and a one-line "
        "summary;\n"
        "- working Met Office source links.\n"
        "Both hourly arrays MUST contain exactly 24 values."
    )
    research = client.research(prompt=prompt, system=_SYSTEM, max_searches=5)
    data = client.parse(
        output_format=_WeatherData,
        system=_SYSTEM,
        prompt=(
            "Structure the weather research below. Both hourly arrays must have "
            "exactly 24 integers. Use only sourced figures.\n\nRESEARCH NOTES:\n"
            + research.text
        ),
        max_tokens=6000,
    )

    warnings = [
        WarnCard(
            sev=(w.sev if w.sev in _VALID_SEV else "yellow"),
            sev_label=w.sev_label, title=w.title, body_html=w.body_html,
        )
        for w in data.warnings
    ]
    days = [
        WeatherDay(
            d=d.d, ic=d.ic, cond=d.cond, hi=d.hi, lo=d.lo, feels=d.feels,
            wind=d.wind, gust=d.gust, hum=d.hum, uv=d.uv, pc=d.pc, mm=d.mm,
            sr=d.sr, ss=d.ss, warn=d.warn, tag=d.tag, sum=d.sum,
        )
        for d in data.days
    ]
    sources = [
        Source(outlet=s.outlet or "Met Office", title=s.title or "forecast", url=s.url)
        for s in data.sources if s.url
    ] or [Source(outlet="Met Office", title="Guildford forecast",
                 url="https://www.metoffice.gov.uk/")]

    return Weather(
        masthead=MastheadWeather(
            temp=data.masthead_temp, cond=data.masthead_cond, low=data.masthead_low,
            rain=data.masthead_rain, gusts=data.masthead_gusts,
        ),
        current_temp=data.current_temp,
        current_cond=data.current_cond,
        current_meta=data.current_meta,
        warnings=warnings,
        hourly_temp=data.hourly_temp,
        hourly_precip=data.hourly_precip,
        days=days,
        sources=sources,
    )
