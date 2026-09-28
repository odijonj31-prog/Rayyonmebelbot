from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

NEXT_STATUS = {
    "new": "confirmed",
    "confirmed": "in_production",
    "in_production": "delivered",
}
STATUS_LABELS = {
    "new": "🆕 Yangi",
    "confirmed": "✅ Kelishuv va to'lov",
    "in_production": "🛠 Ishlab chiqarilmoqda",
    "delivered": "🚚 Yetkazib berildi",
    "cancelled": "❌ Bekor qilingan",
}


def admin_menu_kb() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="🖼 Portfolio qo'shish"), KeyboardButton(text="📋 Portfolio ro'yxati")],
        [KeyboardButton(text="🗑 Portfolio o'chirish"), KeyboardButton(text="🧱 Material qo'shish")],
        [KeyboardButton(text="📢 Kanal qo'shish"), KeyboardButton(text="📋 Kanallar ro'yxati")],
        [KeyboardButton(text="💰 Bazaviy narx (m²)"), KeyboardButton(text="📦 Buyurtmalar")],
        [KeyboardButton(text="📨 Xabar yuborish"), KeyboardButton(text="📊 Statistika")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def channels_list_kb(channels) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        status = "🟢" if ch.is_active else "🔴"
        builder.row(
            InlineKeyboardButton(text=f"{status} {ch.title}", callback_data=f"admin_ch_toggle:{ch.id}"),
            InlineKeyboardButton(text="🗑", callback_data=f"admin_ch_delete:{ch.id}"),
        )
    return builder.as_markup()


def confirm_broadcast_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Yuborish", callback_data="broadcast_confirm"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast_cancel"),
    )
    return builder.as_markup()


def order_admin_kb(order) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    next_status = NEXT_STATUS.get(order.status)
    if next_status:
        builder.row(InlineKeyboardButton(
            text=f"➡️ {STATUS_LABELS[next_status]}", callback_data=f"order_next:{order.id}"
        ))
    builder.row(InlineKeyboardButton(text="💰 Narx belgilash", callback_data=f"order_price:{order.id}"))
    builder.row(InlineKeyboardButton(text="💵 To'lov qo'shish", callback_data=f"order_pay:{order.id}"))
    if order.status != "cancelled":
        builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"order_cancel:{order.id}"))
    return builder.as_markup()
