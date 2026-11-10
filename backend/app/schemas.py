"""Kiruvchi ma’lumotlar sxemalari (pydantic). Noma’lum maydonlar e’tiborsiz qoldiriladi, uzunliklar cheklangan."""
from __future__ import annotations

import re
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from . import common as C

Str = lambda n: Annotated[str, Field(max_length=n)]  # noqa: E731
TG_RE = re.compile(r'^@?[A-Za-z][\w]{4,31}$')


class In(BaseModel):
    model_config = ConfigDict(extra='ignore', str_strip_whitespace=True)


def _empty_none(v):
    return None if v in ('', None) else v


NAME_RE = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ɏЀ-ӿʻʼ‘’'`\- ]+$")


def _person_name(v):
    """Ism/familiya: 2–40 harf (lotin, kirill, o‘ g‘ belgilari, defis). Ortiqcha bo‘sh joylar olib tashlanadi."""
    if v is None:
        return v
    v = re.sub(r'\s+', ' ', v).strip()
    if not v:
        return None
    if len(v) < 2:
        raise ValueError('Kamida 2 ta harf kiriting')
    if len(v) > 40:
        raise ValueError('Ko‘pi bilan 40 ta belgi')
    if not NAME_RE.match(v):
        raise ValueError('Faqat harflar kiriting (raqam va belgilarsiz)')
    return v


def password_policy(v: str) -> str:
    if len(v) < 8:
        raise ValueError('Parol kamida 8 ta belgidan iborat bo‘lsin')
    if not re.search(r'[A-Za-zА-Яа-яЁё]', v) or not re.search(r'\d', v):
        raise ValueError('Parolda kamida bitta harf va bitta raqam bo‘lsin')
    if v.strip() != v:
        raise ValueError('Parol bo‘sh joy bilan boshlanmasin yoki tugamasin')
    return v


def _tg_handle(v):
    v = _empty_none(v.strip() if isinstance(v, str) else v)
    if v is None:
        return None
    if not isinstance(v, str) or not TG_RE.match(v):
        raise ValueError('Telegram username noto‘g‘ri (masalan: @talaba_go)')
    return '@' + v.lstrip('@')


class FileRef(In):
    url: Str(300)
    name: Str(160) = ''
    size: int | None = None

    @field_validator('url')
    @classmethod
    def _media(cls, v):
        if not C.is_media_url(v):
            raise ValueError('Fayl /media/ orqali yuklangan bo‘lishi kerak')
        return v


class ProfileIn(In):
    firstName: Str(60) | None = None
    lastName: Str(60) | None = None
    phone: Str(30) | None = None
    telegram: Str(40) | None = None
    language: Literal['uz', 'uz-Cyrl', 'ru', 'en'] | None = None
    birthDate: Str(10) | None = None
    university: Str(120) | None = None
    faculty: Str(120) | None = None
    course: int | None = Field(None, ge=1, le=7)
    shift: Literal[C.SHIFTS] | None = None
    city: Str(60) | None = None
    district: Str(60) | None = None
    skills: list[Str(40)] | None = Field(None, max_length=30)
    about: Str(1000) | None = None
    cv: FileRef | None = None
    company: Str(120) | None = None
    industry: Str(80) | None = None
    address: Str(200) | None = None
    position: Str(80) | None = None
    logo: Str(300) | None = None
    notifyApp: bool | None = None       # ilova ichidagi bildirishnomalar
    notifyTelegram: bool | None = None  # bot orqali Telegram xabarlari

    _n = field_validator('birthDate', 'course', 'shift', 'telegram', 'logo', mode='before')(classmethod(lambda cls, v: _empty_none(v)))

    @field_validator('phone')
    @classmethod
    def _phone(cls, v):
        if v is None:
            return v
        problem = C.phone_problem(v)
        if problem:
            raise ValueError(problem)
        return C.normalize_phone(v)

    @field_validator('firstName', 'lastName')
    @classmethod
    def _name(cls, v):
        return _person_name(v)

    @field_validator('telegram')
    @classmethod
    def _tg(cls, v):
        if v is None:
            return v
        if not TG_RE.match(v):
            raise ValueError('Telegram username noto‘g‘ri')
        return '@' + v.lstrip('@')

    @field_validator('birthDate')
    @classmethod
    def _date(cls, v):
        if not v:
            return v
        try:
            d = date.fromisoformat(v)
        except ValueError:
            raise ValueError('Sana formati noto‘g‘ri (YYYY-MM-DD)') from None
        age = (date.today() - d).days / 365.25
        if not 14 <= age <= 70:
            raise ValueError('Tug‘ilgan sana noto‘g‘ri: yosh 14 dan 70 gacha bo‘lishi kerak')
        return v

    @field_validator('logo')
    @classmethod
    def _logo(cls, v):
        if v and not C.is_media_url(v):
            raise ValueError('Logo /media/ orqali yuklanishi kerak')
        return v


class RegisterIn(ProfileIn):
    role: Literal[C.ROLES]
    firstName: Str(40)
    lastName: Str(40)
    phone: Str(30)
    password: Str(128) | None = None
    initData: Str(4096) | None = None

    @field_validator('firstName', 'lastName', mode='before')
    @classmethod
    def _required_name(cls, v):
        if not (isinstance(v, str) and v.strip()):
            raise ValueError('Majburiy maydon')
        return v

    @field_validator('password')
    @classmethod
    def _pw(cls, v):
        return password_policy(v) if v is not None else v


class LoginIn(In):
    phone: Str(30)
    password: Str(128)


class TelegramAuthIn(In):
    initData: Str(4096)


class PasswordIn(In):
    current: Str(128) = ''
    next: Str(128)

    @field_validator('next')
    @classmethod
    def _pw(cls, v):
        return password_policy(v)


class AdminLoginIn(In):
    username: Str(64)
    password: Str(128)


# ----------------------------------------------------------------- e’lonlar
class JobIn(In):
    title: Str(120) = Field(min_length=3)
    company: Str(120) = Field(min_length=2)
    city: Str(60) = 'Toshkent'
    district: Str(60) | None = None
    format: Literal[C.JOB_FORMATS]
    type: Literal[C.JOB_TYPES]
    salary: int = Field(gt=0, le=1_000_000_000)
    salaryPeriod: Literal[C.SALARY_PERIODS]
    workTime: Literal[C.WORK_TIMES] = 'flexible'
    schedule: Str(120) = ''
    category: Str(60) = ''
    description: Str(3000) = Field(min_length=20)
    requirements: list[Str(200)] = Field(default_factory=list, max_length=20)
    tags: list[Str(40)] = Field(default_factory=list, max_length=10)
    phone: Str(30) | None = None
    telegram: Str(40) | None = None

    @field_validator('phone')
    @classmethod
    def _phone(cls, v):
        if not v:
            return None
        p = C.normalize_phone(v)
        if not p:
            raise ValueError('Telefon raqam noto‘g‘ri: +998 XX XXX XX XX')
        return p

    @field_validator('telegram', mode='before')
    @classmethod
    def _tg(cls, v):
        return _tg_handle(v)


class HouseIn(In):
    title: Str(120) = Field(min_length=3)
    type: Literal[C.HOUSE_TYPES]
    photos: list[Str(300)] = Field(min_length=3, max_length=10)
    city: Str(60) = 'Toshkent'
    district: Str(60) = Field(min_length=2)
    address: Str(200) = Field(min_length=2)
    rooms: int = Field(ge=1, le=20)
    area: float | None = Field(None, ge=1, le=2000)
    price: int = Field(gt=0, le=1_000_000_000)
    audience: Literal[C.AUDIENCES] = 'any'
    capacity: int = Field(1, ge=1, le=50)
    freeSpots: int = Field(1, ge=0, le=50)
    amenities: list[Str(40)] = Field(default_factory=list, max_length=20)
    description: Str(3000) = Field(min_length=20)
    phone: Str(30) | None = None
    telegram: Str(40) | None = None
    lat: float | None = Field(None, ge=-90, le=90)
    lng: float | None = Field(None, ge=-180, le=180)

    _a = field_validator('area', mode='before')(classmethod(lambda cls, v: _empty_none(v)))

    @field_validator('photos')
    @classmethod
    def _photos(cls, v):
        if not all(C.is_media_url(p) for p in v):
            raise ValueError('Rasmlar /media/ orqali yuklanishi kerak')
        return v

    @field_validator('phone')
    @classmethod
    def _phone(cls, v):
        if not v:
            return None
        p = C.normalize_phone(v)
        if not p:
            raise ValueError('Telefon raqam noto‘g‘ri: +998 XX XXX XX XX')
        return p

    @field_validator('telegram', mode='before')
    @classmethod
    def _tg(cls, v):
        return _tg_handle(v)


class ActiveIn(In):
    active: bool


class OccupancyIn(In):
    occupancy: Literal[C.OCCUPANCY]


class ApplyIn(In):
    message: Str(1000) = ''


class RentRequestIn(In):
    message: Str(1000) = ''
    moveIn: Str(10) = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    term: Literal[C.RENT_TERMS] = '6'


class AppStatusIn(In):
    status: Literal['viewed', 'interview', 'accepted', 'declined']
    interviewAt: Str(40) | None = None
    note: Str(500) | None = None


class ReqStatusIn(In):
    status: Literal['viewed', 'accepted', 'declined']
    note: Str(500) | None = None


class CompleteLessonIn(In):
    answers: list[int] | None = Field(None, max_length=20)
    score: int | None = Field(None, ge=0, le=20)


# ----------------------------------------------------------------- support / shikoyat
class Attachment(In):
    url: Str(300)
    name: Str(160) = 'fayl'

    @field_validator('url')
    @classmethod
    def _m(cls, v):
        if not C.is_media_url(v):
            raise ValueError('Fayl /media/ orqali yuklanishi kerak')
        return v


class TicketIn(In):
    type: Literal[C.TICKET_TYPES]
    subject: Str(120) = Field(min_length=3)
    text: Str(4000) = Field(min_length=5)
    attachment: Attachment | None = None


class MessageIn(In):
    text: Str(4000) = ''
    attachment: Attachment | None = None


class ComplaintTarget(In):
    type: Literal['job', 'house', 'user']
    id: Str(40)
    label: Str(200) = ''


class ComplaintIn(In):
    target: ComplaintTarget
    category: Str(80) = Field(min_length=2)
    message: Str(2000) = ''