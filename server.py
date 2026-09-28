import os
import json
import httpx
from aiohttp import web

from config import BOT_TOKEN, COMPANY_NAME, MANAGER_USERNAME, ANTHROPIC_API_KEY
from api.security import validate_init_data
from api.ai_pricing import explain_price
from database.requests import (
    get_or_create_user, get_active_portfolio, get_active_options, get_options_by_ids,
    get_setting, create_order, get_orders_with_payments, get_user,
)

WEBAPP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "webapp")

routes = web.RouteTableDef()


async def _identify_user(request: web.Request, body: dict):
    """initData'ni tekshirib, bazadagi User obyektini qaytaradi (yoki None)."""
    init_data = body.get("initData", "")
    parsed = validate_init_data(init_data)
    if not parsed:
        return None
    user_json = parsed.get("user")
    if not user_json:
        return None
    tg_user = json.loads(user_json)
    user = await get_or_create_user(
        telegram_id=tg_user["id"],
        username=tg_user.get("username"),
        full_name=f'{tg_user.get("first_name", "")} {tg_user.get("last_name", "")}'.strip(),
    )
    return user


@routes.get("/")
async def index(request: web.Request):
    return web.FileResponse(os.path.join(WEBAPP_DIR, "index.html"))


@routes.get("/health")
async def health(request: web.Request):
    return web.json_response({"ok": True, "service": COMPANY_NAME})


@routes.get("/api/config")
async def api_config(request: web.Request):
    return web.json_response({
        "ok": True,
        "company_name": COMPANY_NAME,
        "manager_username": MANAGER_USERNAME,
        "has_ai": bool(ANTHROPIC_API_KEY),
    })


@routes.post("/api/validate")
async def api_validate(request: web.Request):
    body = await request.json()
    user = await _identify_user(request, body)
    if not user:
        return web.json_response({"ok": False, "error": "invalid_init_data"}, status=401)
    return web.json_response({
        "ok": True,
        "user": {"id": user.id, "telegram_id": user.telegram_id, "full_name": user.full_name},
    })


@routes.get("/api/portfolio")
async def api_portfolio(request: web.Request):
    items = await get_active_portfolio()
    return web.json_response({
        "ok": True,
        "items": [
            {
                "id": item.id,
                "title": item.title,
                "description": item.description,
                "style_tags": item.style_tags,
                "photo_url": f"/api/photo/{item.photo_file_id}",
            }
            for item in items
        ],
    })


@routes.get("/api/photo/{file_id}")
async def api_photo(request: web.Request):
    file_id = request.match_info["file_id"]
    async with httpx.AsyncClient() as client:
        file_resp = await client.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile", params={"file_id": file_id})
        file_data = file_resp.json()
        if not file_data.get("ok"):
            return web.json_response({"ok": False, "error": "file_not_found"}, status=404)
        file_path = file_data["result"]["file_path"]
        photo_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        photo_resp = await client.get(photo_url)
        return web.Response(body=photo_resp.content, content_type="image/jpeg")


@routes.get("/api/options")
async def api_options(request: web.Request):
    options = await get_active_options()
    grouped = {"material": [], "color": [], "part": []}
    for o in options:
        if o.category in grouped:
            grouped[o.category].append({"id": o.id, "name": o.name, "extra_price": o.extra_price})
    base_rate_raw = await get_setting("base_price_per_sqm", "0")
    return web.json_response({"ok": True, "options": grouped, "base_price_per_sqm": int(base_rate_raw)})


@routes.post("/api/estimate")
async def api_estimate(request: web.Request):
    body = await request.json()
    width = int(body.get("width_mm") or 0)
    height = int(body.get("height_mm") or 0)
    depth = body.get("depth_mm")
    depth = int(depth) if depth else None
    option_ids = body.get("option_ids") or []
    description = body.get("description")

    if width <= 0 or height <= 0:
        return web.json_response({"ok": False, "error": "invalid_dimensions"}, status=400)

    selected = await get_options_by_ids(option_ids)
    base_rate_raw = await get_setting("base_price_per_sqm", "0")
    base_rate = int(base_rate_raw)

    sqm = (width / 1000) * (height / 1000)
    total = int(sqm * base_rate) + sum(o.extra_price for o in selected)

    options_payload = [{"name": o.name, "extra_price": o.extra_price} for o in selected]
    explanation = await explain_price(width, height, depth, options_payload, total, description)

    return web.json_response({
        "ok": True,
        "estimated_price": total,
        "explanation": explanation,
        "breakdown": {
            "base": int(sqm * base_rate),
            "options": [{"name": o.name, "extra_price": o.extra_price} for o in selected],
        },
    })


@routes.post("/api/orders")
async def api_create_order(request: web.Request):
    body = await request.json()
    user = await _identify_user(request, body)
    if not user:
        return web.json_response({"ok": False, "error": "invalid_init_data"}, status=401)

    width = int(body.get("width_mm") or 0)
    height = int(body.get("height_mm") or 0)
    depth = body.get("depth_mm")
    depth = int(depth) if depth else None
    option_ids = body.get("option_ids") or []
    description = body.get("description")
    estimated_price = body.get("estimated_price")
    portfolio_item_id = body.get("portfolio_item_id")
    contact_name = body.get("contact_name")
    contact_phone = body.get("contact_phone")

    order = await create_order(
        user_id=user.id, width_mm=width, height_mm=height, depth_mm=depth,
        selected_option_ids=option_ids, ai_estimated_price=estimated_price,
        description=description, portfolio_item_id=portfolio_item_id,
        contact_name=contact_name, contact_phone=contact_phone,
    )

    bot = request.app["bot"]
    from config import SUPER_ADMIN_IDS
    price_line = f"💰 Taxminiy narx: {estimated_price:,} so'm\n".replace(",", " ")
    text = (
        f"🆕 <b>Yangi buyurtma (Mini App)</b>\n\n"
        f"👤 {contact_name or user.full_name} — {contact_phone or '—'}\n"
        f"🆔 <code>{user.telegram_id}</code> (@{user.username or '—'})\n"
        f"📐 O'lcham: {width}x{height}" + (f"x{depth}" if depth else "") + " mm\n"
        + price_line +
        f"📝 Izoh: {description or '—'}\n"
        f"🔢 Buyurtma ID: {order.id}"
    )
    for admin_id in SUPER_ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            pass

    return web.json_response({"ok": True, "order_id": order.id})


@routes.post("/api/orders/mine")
async def api_my_orders(request: web.Request):
    body = await request.json()
    user = await _identify_user(request, body)
    if not user:
        return web.json_response({"ok": False, "error": "invalid_init_data"}, status=401)

    rows = await get_orders_with_payments(user.id)
    status_labels = {
        "new": "🆕 Yangi", "reviewing": "🔎 Ko'rib chiqilmoqda", "confirmed": "✅ Tasdiqlangan",
        "in_production": "🛠 Ishlanmoqda", "ready": "📦 Tayyor", "delivered": "🚚 Yetkazildi",
        "cancelled": "❌ Bekor qilingan",
    }
    return web.json_response({
        "ok": True,
        "orders": [
            {
                "id": r["order"].id,
                "status": r["order"].status,
                "status_label": status_labels.get(r["order"].status, r["order"].status),
                "width_mm": r["order"].width_mm,
                "height_mm": r["order"].height_mm,
                "estimated_price": r["order"].ai_estimated_price,
                "agreed_price": r["order"].agreed_price,
                "paid": r["paid"],
                "debt": r["debt"],
                "created_at": r["order"].created_at.isoformat(),
            }
            for r in rows
        ],
    })


def create_app(bot=None) -> web.Application:
    app = web.Application()
    app["bot"] = bot
    app.add_routes(routes)
    app.router.add_static("/assets/", path=WEBAPP_DIR, name="assets")
    return app
