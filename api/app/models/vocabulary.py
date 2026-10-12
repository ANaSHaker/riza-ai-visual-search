"""Open-vocabulary prompts for the garment detector.

The prompts are deliberately specific ("a pair of heels" instead of "shoes")
because OWLv2 produces far fewer false positives with descriptive phrases.
Each prompt carries a short display label (English + Arabic, the storefront was
bilingual), an icon for the UI chip, and a *domain*:

* ``fashion`` — apparel, footwear, accessories (FashionCLIP's home turf)
* ``general`` — beauty, fragrance, toys, stationery; searched with a slightly
  stricter similarity threshold because FashionCLIP is less specialised there.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Domain = Literal["fashion", "general"]


@dataclass(frozen=True)
class DetectionLabel:
    prompt: str
    label: str
    label_ar: str
    icon: str
    domain: Domain = "fashion"


VOCABULARY: tuple[DetectionLabel, ...] = (
    # women
    DetectionLabel("a woman wearing a dress", "Dress", "فستان", "👗"),
    DetectionLabel("a woman wearing a blouse", "Blouse", "بلوزة", "👚"),
    DetectionLabel("a women's abaya", "Abaya", "عباية", "👘"),
    DetectionLabel("a women's skirt", "Skirt", "تنورة", "👗"),
    DetectionLabel("a women's sweater", "Sweater", "سويتر", "🧥"),
    DetectionLabel("a women's coat", "Coat", "معطف", "🧥"),
    # men
    DetectionLabel("a men's t-shirt", "T-shirt", "تيشيرت", "👕"),
    DetectionLabel("a men's shirt", "Shirt", "قميص", "👔"),
    DetectionLabel("a men's jacket", "Jacket", "جاكيت", "🧥"),
    DetectionLabel("men's pants", "Pants", "بنطلون", "👖"),
    DetectionLabel("men's shorts", "Shorts", "شورت", "🩳"),
    # footwear
    DetectionLabel("a pair of sandals", "Sandals", "صندل", "👡"),
    DetectionLabel("a pair of heels", "Heels", "هيلز", "👠"),
    DetectionLabel("a pair of sneakers", "Sneakers", "كوتشي", "👟"),
    DetectionLabel("a pair of boots", "Boots", "بوت", "👢"),
    DetectionLabel("a pair of shoes", "Shoes", "حذاء", "👞"),
    # accessories
    DetectionLabel("a wristwatch on a wrist", "Watch", "ساعة", "⌚"),
    DetectionLabel("a leather handbag", "Handbag", "حقيبة", "👜"),
    DetectionLabel("a backpack", "Backpack", "حقيبة ظهر", "🎒"),
    DetectionLabel("a belt", "Belt", "حزام", "🪢"),
    DetectionLabel("sunglasses", "Sunglasses", "نظارة شمسية", "🕶️"),
    # beauty & care
    DetectionLabel("a skincare cream jar", "Cream", "كريم", "🧴", "general"),
    DetectionLabel("a lotion or serum bottle", "Serum", "سيروم", "🧴", "general"),
    DetectionLabel("a lipstick tube", "Lipstick", "أحمر شفاه", "💄", "general"),
    DetectionLabel("a mascara tube", "Mascara", "ماسكارا", "💄", "general"),
    DetectionLabel("a makeup palette", "Makeup palette", "باليت مكياج", "🖌️", "general"),
    DetectionLabel("a shampoo bottle", "Shampoo", "شامبو", "🧴", "general"),
    # fragrance
    DetectionLabel("a perfume bottle", "Perfume", "عطر", "🧴", "general"),
    DetectionLabel("an incense burner", "Incense burner", "مبخرة", "🪔", "general"),
    DetectionLabel("incense sticks", "Incense", "بخور", "🕯️", "general"),
    # kids & school
    DetectionLabel("a children toy", "Toy", "لعبة أطفال", "🧸", "general"),
    DetectionLabel("a stuffed animal", "Plush toy", "دمية محشوة", "🧸", "general"),
    DetectionLabel("building blocks toy", "Blocks", "مكعبات", "🧩", "general"),
    DetectionLabel("stationery items", "Stationery", "أدوات مدرسية", "✏️", "general"),
    DetectionLabel("a pencil or pen", "Pen", "قلم", "✏️", "general"),
    DetectionLabel("a notebook", "Notebook", "دفتر", "📓", "general"),
)

PROMPTS: tuple[str, ...] = tuple(v.prompt for v in VOCABULARY)

# Returned when nothing is detected: search the whole image as one item.
WHOLE_IMAGE = DetectionLabel("product", "Product", "منتج", "🛍️")
