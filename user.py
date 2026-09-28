from aiogram import Router, Bot, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import WEBAPP_URL, COMPANY_NAME
from database.requests import get_or_create_user
from filters.subscription import get_unsubscribed_channels

router = Router()


def open_app_kb() -> InlineKeyboardMarkup:
    builder = [[InlineKeyboardButton(text="🛋 Ilovani ochish", web_app=WebAppInfo(url=WEBAPP_URL))]]
    return InlineKeyboardMarkup(inline_keyboard=builder)


def subscription_kb(channels) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        url = ch.invite_link or (f"https://t.me/{ch.username.lstrip('@')}" if ch.username else ch.invite_link)
        builder.row(InlineKeyboardButton(text=f"🔒 {ch.title}", url=url))
    builder.row(InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_subscription"))
    return builder.as_markup()


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    unsubscribed = await get_unsubscribed_channels(bot, message.from_user.id)
    if unsubscribed:
        await message.answer(
            "👋 Botdan to'liq foydalanish uchun quyidagi kanal(lar)ga obuna bo'ling!",
            reply_markup=subscription_kb(unsubscribed),
        )
        return

    await send_welcome(message)


async def send_welcome(message: Message):
    if not WEBAPP_URL:
        await message.answer(
            f"👋 Assalomu alaykum, {message.from_user.first_name}!\n"
            f"🛋 <b>{COMPANY_NAME}</b> botiga xush kelibsiz!\n\n"
            f"⚠️ Mini App hali sozlanmagan (WEBAPP_URL yo'q)."
        )
        return

    await message.answer(
        f"👋 Assalomu alaykum, {message.from_user.first_name}!\n"
        f"🛋 <b>{COMPANY_NAME}</b> botiga xush kelibsiz!\n\n"
        f"Quyidagi tugma orqali ilovani oching — katalog, buyurtma va boshqa "
        f"barcha imkoniyatlar shu yerda:",
        reply_markup=open_app_kb(),
    )


@router.callback_query(F.data == "check_subscription")
async def check_subscription(callback: CallbackQuery, bot: Bot):
    unsubscribed = await get_unsubscribed_channels(bot, callback.from_user.id)
    if unsubscribed:
        await callback.answer("❌ Hali barcha kanallarga obuna bo'lmadingiz!", show_alert=True)
        return
    await callback.message.delete()
    await send_welcome(callback.message)
    await callback.answer()
