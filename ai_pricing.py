import json
import httpx

from config import ANTHROPIC_API_KEY

ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"


async def explain_price(width_mm: int, height_mm: int, depth_mm: int | None,
                         options: list[dict], base_total: int, style_description: str | None) -> str:
    """
    Narxning o'zi HAR DOIM aniq formula bilan (deterministik) hisoblanadi — AI narxni
    o'zgartirmaydi, faqat mijozga tushunarli, do'stona tarzda tushuntirib beradi.
    Agar ANTHROPIC_API_KEY sozlanmagan bo'lsa, oddiy shablon matn qaytariladi.
    """
    options_text = ", ".join(f"{o['name']} (+{o['extra_price']:,} so'm)".replace(",", " ") for o in options) or "—"

    if not ANTHROPIC_API_KEY:
        return (
            f"Tanlangan o'lcham: {width_mm}x{height_mm}"
            + (f"x{depth_mm}" if depth_mm else "")
            + f" mm.\nQo'shimchalar: {options_text}.\n"
            + f"Taxminiy narx: {base_total:,} so'm.".replace(",", " ")
        )

    system_prompt = (
        "Sen RAYYON Mebel ustaxonasining do'stona AI maslahatchisisan. Mijozga uning "
        "buyurtmasi bo'yicha taxminiy narx qanday shakllanganini QISQA (2-4 gap), "
        "iliq va tushunarli tilda, o'zbek tilida tushuntir. Narxning o'zini o'zgartirma — "
        "u allaqachon hisoblangan, sen faqat tushuntirasan. Faqat mebel mavzusida gapir."
    )
    user_prompt = (
        f"O'lcham: {width_mm}x{height_mm}" + (f"x{depth_mm}" if depth_mm else "") + " mm\n"
        f"Tanlangan variantlar: {options_text}\n"
        f"Uslub/tavsif: {style_description or '—'}\n"
        f"Yakuniy taxminiy narx: {base_total:,} so'm".replace(",", " ")
    )

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": ANTHROPIC_MODEL,
                    "max_tokens": 250,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}],
                },
            )
            data = resp.json()
            text_block = next(b["text"] for b in data["content"] if b["type"] == "text")
            return text_block.strip()
    except Exception:
        return (
            f"Tanlangan o'lcham: {width_mm}x{height_mm}"
            + (f"x{depth_mm}" if depth_mm else "")
            + f" mm.\nQo'shimchalar: {options_text}.\n"
            + f"Taxminiy narx: {base_total:,} so'm.".replace(",", " ")
        )
