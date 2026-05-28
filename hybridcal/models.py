from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationInfo
import zoneinfo

EventStatus = Literal["confirmed", "tentative", "cancelled"]
EventSource = Literal["organizer", "community", "scraped"]


class Location(BaseModel):
    city: str
    country: str = Field(..., pattern=r"^[A-Z]{2}$")
    venue: str | None = None
    timezone: str
    lat: float | None = None
    lon: float | None = None

    @field_validator("timezone")
    @classmethod
    def validate_tz(cls, v: str) -> str:
        try:
            zoneinfo.ZoneInfo(v)
        except zoneinfo.ZoneInfoNotFoundError:
            raise ValueError(f"Invalid IANA timezone: {v}")
        return v


class ScheduleEntry(BaseModel):
    category: str
    day: date
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")


class Event(BaseModel):
    slug: str = Field(..., pattern=r"^[a-z0-9-]+$")
    name: str
    format: str
    # Both null = TBA (date not yet announced). If only one is provided,
    # the other is filled to match (single-day event convenience).
    date_start: date | None = None
    date_end: date | None = None
    location: Location
    url: str
    status: EventStatus = "confirmed"
    source: EventSource = "community"
    categories: list[str] = Field(default_factory=list)
    schedule_url: str | None = None
    schedule_updated_at: date | None = None
    schedule: list[ScheduleEntry] = Field(default_factory=list)
    notes: str | None = None

    @model_validator(mode="after")
    def normalize_dates(self):
        # If exactly one date is set, mirror it into the other.
        if self.date_start is None and self.date_end is not None:
            self.date_start = self.date_end
        elif self.date_end is None and self.date_start is not None:
            self.date_end = self.date_start
        # If both are set, ensure end >= start.
        if self.date_start and self.date_end and self.date_end < self.date_start:
            raise ValueError("date_end must be >= date_start")
        return self

    @property
    def is_tba(self) -> bool:
        return self.date_start is None


class Format(BaseModel):
    name: str
    name_de: str | None = None  # optional per-language override
    name_en: str | None = None
    type: str
    website: str | None = None
    description_de: str | None = None
    description_en: str | None = None
    long_description_de: str | None = None  # markdown body for detail page
    long_description_en: str | None = None
    color: str | None = None  # hex, used for map markers and badges


class Category(BaseModel):
    id: str
    label_de: str | None = None
    label_en: str | None = None


class Region(BaseModel):
    id: str
    name_de: str
    name_en: str
    countries: list[str] = Field(default_factory=list)


class Site(BaseModel):
    url: str
    github_repo: str
    web3forms_key: str
    default_language: str
    default_regions: list[str] = Field(default_factory=lambda: ["dach"])
    base_path: str = ""  # e.g. "/hybridcal" for GitHub project pages, "" for custom domain
    custom_domain: str | None = None  # if set, build writes dist/CNAME (GitHub Pages picks it up)
    google_site_verification: str | None = None  # GSC HTML-tag verification token
