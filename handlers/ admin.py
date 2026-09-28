from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from filters.is_admin import IsAdmin
from keyboards.admin_kb import (
    admin_menu_kb, channels_list_kb, confirm_broadcast_kb, order_admin_kb,
    NEXT_STATUS, STATUS_LABELS,
)
from database.requests import (
    add_portfolio_item, get_active_portfolio, delete_portfolio_item,
    add_materials_bulk, get_active_options, delete_material_option,
    count_users, count_orders, get_all_user_ids,
    add_channel, get_active_channels, remove_channel, toggle_channel,
    get_setting, set_setting,
    get_all_orders, get_order, update_order_status, set_order_agreed_price,
    add_payment, get_total_paid, get_user_by_id,
)
from states import (
    AddPortfolio, AddMaterialBulk, DeletePortfolio, AddChannel, Broadcast,
    SetBasePrice, SetAgreedPrice, AddPayment,
)

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

MENU_TEXTS = {
    "🖼 Portfolio qo'shish", "🗑 Portfolio o'chirish", "📋 Portfolio ro'yxati",
    "🧱 Material qo'shish", "📢 Kanal qo'shish", "📋 Kanallar ro'yxati",
    "💰 Bazaviy narx (m²)", "📦 Buyurtmalar", "📨 Xabar yuborish", "📊 Statistika",
}


@router.message(Command("admin"))
async def open_admin(message: Message):
    await message.answer("🛠 Admin panelga xush kelibsiz!", reply_markup=admin_menu_kb())


@router.message(Command("cancel"))
async def admin_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu_kb())


# ---------- PORTFOLIO ----------

@router.message(F.text == "🖼 Portfolio qo'shish")
async def add_portfolio_start(message: Message, state: FSMContext):
    await state.set_state(AddPortfolio.waiting_photo)
    await message.answer("🖼 Ish rasmini yuboring:\n\n(Bekor qilish uchun /cancel)")


@router.message(AddPortfolio.waiting_photo, F.photo)
async def add_portfolio_photo(message: Message, state: FSMContext):
    await state.update_data(photo_file_id=message.photo[-1].file_id)
    await state.set_state(AddPortfolio.waiting_title)
    await message.answer("📝 Sarlavha kiriting:")


@router.message(AddPortfolio.waiting_photo)
async def add_portfolio_photo_wrong(message: Message, state: FSMContext):
    if message.text in MENU_TEXTS:
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu_kb())
        return
    await message.answer("❗️ Iltimos, rasm yuboring.")


@router.message(AddPortfolio.waiting_title)
async def add_portfolio_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(AddPortfolio.waiting_description)
    await message.answer("📄 Tavsif kiriting (yoki /skip):")


@router.message(AddPortfolio.waiting_description, Command("skip"))
async def add_portfolio_desc_skip(message: Message, state: FSMContext):
    await state.update_data(description=None)
    await state.set_state(AddPortfolio.waiting_tags)
    await message.answer("🏷 Uslub teglari, vergul bilan (yoki /skip):")


@router.message(AddPortfolio.waiting_description)
async def add_portfolio_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(AddPortfolio.waiting_tags)
    await message.answer("🏷 Uslub teglari, vergul bilan (yoki /skip):")


@router.message(AddPortfolio.waiting_tags, Command("skip"))
async def add_portfolio_tags_skip(message: Message, state: FSMContext):
    await finalize_portfolio(message, state, tags=None)


@router.message(AddPortfolio.waiting_tags)
async def add_portfolio_tags(message: Message, state: FSMContext):
    await finalize_portfolio(message, state, tags=message.text.strip())


async def finalize_portfolio(message: Message, state: FSMContext, tags):
    data = await state.get_data()
    await state.clear()
    item = await add_portfolio_item(
        title=data["title"], photo_file_id=data["photo_file_id"],
        description=data.get("description"), style_tags=tags,
    )
    await message.answer(f"✅ Portfolio qo'shildi! ID: {item.id}", reply_markup=admin_menu_kb())


@router.message(F.text == "📋 Portfolio ro'yxati")
async def list_portfolio(message: Message):
    items = await get_active_portfolio()
    if not items:
        await message.answer("Hozircha portfolio bo'sh.")
        return
    text = "📋 <b>Portfolio:</b>\n\n" + "\n".join(f"🆔 {i.id} — {i.title}" for i in items)
    await message.answer(text)


@router.message(F.text == "🗑 Portfolio o'chirish")
async def delete_portfolio_start(message: Message, state: FSMContext):
    await state.set_state(DeletePortfolio.waiting_id)
    await message.answer("🆔 O'chirmoqchi bo'lgan ID:\n\n(Bekor qilish uchun /cancel)")


@router.message(DeletePortfolio.waiting_id)
async def delete_portfolio_process(message: Message, state: FSMContext):
    await state.clear()
    try:
        item_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting.", reply_markup=admin_menu_kb())
        return
    ok = await delete_portfolio_item(item_id)
    await message.answer(f"✅ #{item_id} o'chirildi." if ok else "❌ Topilmadi.", reply_markup=admin_menu_kb())


# ---------- MATERIAL — TEZKOR (BULK) QO'SHISH ----------

@router.message(F.text == "🧱 Material qo'shish")
async def add_material_start(message: Message, state: FSMContext):
    await state.set_state(AddMaterialBulk.waiting_category)
    await message.answer(
        "🧱 Qaysi turkumga qo'shamiz?\n\n"
        "<code>material</code> — xomashyo (masalan: Yong'oq shponi)\n"
        "<code>color</code> — rang\n"
        "<code>part</code> — zapchast/aksessuar\n\n"
        "Birini yozing (masalan: material)\n\n(Bekor qilish uchun /cancel)"
    )


@router.message(AddMaterialBulk.waiting_category)
async def add_material_category(message: Message, state: FSMContext):
    category = message.text.strip().lower()
    if category not in ("material", "color", "part"):
        await message.answer("❌ Faqat: material, color yoki part deb yozing.")
        return
    await state.update_data(category=category)
    await state.set_state(AddMaterialBulk.waiting_lines)
    await message.answer(
        "📝 Endi nomlarni va narxlarini yuboring — <b>har qatorda bittadan</b>, shu formatda:\n\n"
        "<code>Yong'oq shponi - 150000\nOq plastik - 80000\nOltin tutqich - 45000</code>\n\n"
        "Bir nechtasini birdan, bitta xabarda yuborishingiz mumkin!\n\n(Bekor qilish uchun /cancel)"
    )


@router.message(AddMaterialBulk.waiting_lines)
async def add_material_lines(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    lines = message.text.strip().split("\n")
    added = await add_materials_bulk(category=data["category"], lines=lines)
    if added:
        await message.answer(f"✅ {added} ta variant qo'shildi ([{data['category']}] turkumiga).", reply_markup=admin_menu_kb())
    else:
        await message.answer(
            "❌ Hech narsa qo'shilmadi. Format: <code>Nomi - narx</code> (har qatorda bittadan)",
            reply_markup=admin_menu_kb(),
        )


# ---------- KANALLAR (majburiy obuna) ----------

@router.message(F.text == "📢 Kanal qo'shish")
async def add_channel_start(message: Message, state: FSMContext):
    await state.set_state(AddChannel.waiting_forward_or_id)
    await message.answer(
        "📢 Botni kanalga <b>admin</b> qilib qo'shing, so'ng kanaldan xabar forward qiling.\n\n"
        "(Bekor qilish uchun /cancel)"
    )


@router.message(AddChannel.waiting_forward_or_id, F.forward_from_chat)
async def add_channel_forward(message: Message, bot: Bot, state: FSMContext):
    await state.clear()
    chat = message.forward_from_chat
    try:
        await bot.get_chat_member(chat.id, bot.id)
    except Exception:
        await message.answer("❌ Bot ushbu kanalda admin emas.", reply_markup=admin_menu_kb())
        return
    invite_link = None
    if not chat.username:
        try:
            invite_link = await bot.export_chat_invite_link(chat.id)
        except Exception:
            pass
    ch = await add_channel(chat_id=chat.id, title=chat.title, username=chat.username, invite_link=invite_link)
    await message.answer(f"✅ Kanal qo'shildi: {ch.title}", reply_markup=admin_menu_kb())


@router.message(AddChannel.waiting_forward_or_id)
async def add_channel_wrong(message: Message, state: FSMContext):
    if message.text in MENU_TEXTS or message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu_kb())
        return
    await message.answer("❗️ Iltimos, kanaldan xabar forward qiling.")


@router.message(F.text == "📋 Kanallar ro'yxati")
async def list_channels(message: Message):
    channels = await get_active_channels()
    if not channels:
        await message.answer("Hozircha kanal qo'shilmagan.")
        return
    await message.answer("📋 <b>Majburiy obuna kanallari:</b>", reply_markup=channels_list_kb(channels))


@router.callback_query(F.data.startswith("admin_ch_toggle:"))
async def toggle_channel_cb(callback: CallbackQuery):
    channel_id = int(callback.data.split(":")[1])
    channels = await get_active_channels()
    ch = next((c for c in channels if c.id == channel_id), None)
    if ch:
        await toggle_channel(channel_id, not ch.is_active)
    channels = await get_active_channels()
    await callback.message.edit_reply_markup(reply_markup=channels_list_kb(channels))
    await callback.answer("O'zgartirildi")


@router.callback_query(F.data.startswith("admin_ch_delete:"))
async def delete_channel_cb(callback: CallbackQuery):
    channel_id = int(callback.data.split(":")[1])
    await remove_channel(channel_id)
    channels = await get_active_channels()
    await callback.message.edit_reply_markup(reply_markup=channels_list_kb(channels))
    await callback.answer("O'chirildi")


# ---------- BAZAVIY NARX ----------

@router.message(F.text == "💰 Bazaviy narx (m²)")
async def set_base_price_start(message: Message, state: FSMContext):
    current = await get_setting("base_price_per_sqm", "0")
    await state.set_state(SetBasePrice.waiting_price)
    await message.answer(
        f"💰 Hozirgi bazaviy narx: {int(current):,} so'm / m²\n\n".replace(",", " ") +
        "Yangi narxni kiriting (so'mda):\n\n(Bekor qilish uchun /cancel)"
    )


@router.message(SetBasePrice.waiting_price)
async def set_base_price_process(message: Message, state: FSMContext):
    await state.clear()
    try:
        price = int(message.text.strip().replace(" ", ""))
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting.", reply_markup=admin_menu_kb())
        return
    await set_setting("base_price_per_sqm", str(price))
    await message.answer(f"✅ Bazaviy narx o'rnatildi: {price:,} so'm/m²".replace(",", " "), reply_markup=admin_menu_kb())


# ---------- STATISTIKA ----------

@router.message(F.text == "📊 Statistika")
async def show_stats(message: Message):
    users = await count_users()
    orders = await count_orders()
    portfolio = await get_active_portfolio()
    materials = await get_active_options()
    await message.answer(
        f"📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: {users}\n"
        f"📦 Buyurtmalar: {orders}\n"
        f"🖼 Portfolio: {len(portfolio)}\n"
        f"🧱 Material variantlari: {len(materials)}"
    )


# ---------- BROADCAST ----------

@router.message(F.text == "📨 Xabar yuborish")
async def broadcast_start(message: Message, state: FSMContext):
    await state.set_state(Broadcast.waiting_content)
    await message.answer("📨 Barcha obunachilarga yubormoqchi bo'lgan xabar/yangilik/so'rovnomani yuboring:\n\n(Bekor qilish uchun /cancel)")


@router.message(Broadcast.waiting_content)
async def broadcast_preview(message: Message, state: FSMContext):
    if message.text in MENU_TEXTS or message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu_kb())
        return
    await state.update_data(chat_id=message.chat.id, message_id=message.message_id)
    await state.set_state(Broadcast.waiting_confirm)
    await message.answer("Yuqoridagi xabarni barchaga yuborishni tasdiqlaysizmi?", reply_markup=confirm_broadcast_kb())


@router.callback_query(Broadcast.waiting_confirm, F.data == "broadcast_confirm")
async def broadcast_confirm(callback: CallbackQuery, bot: Bot, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    user_ids = await get_all_user_ids()
    sent, failed = 0, 0
    await callback.message.edit_text(f"⏳ Yuborilmoqda... (0/{len(user_ids)})")
    for uid in user_ids:
        try:
            await bot.copy_message(chat_id=uid, from_chat_id=data["chat_id"], message_id=data["message_id"])
            sent += 1
        except Exception:
            failed += 1
    await callback.message.edit_text(f"✅ Yuborildi: {sent}\n❌ Yuborilmadi: {failed}")


@router.callback_query(Broadcast.waiting_confirm, F.data == "broadcast_cancel")
async def broadcast_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi.")


# ---------- BUYURTMALAR BOSHQARUVI ----------

async def format_order_text(order) -> str:
    user = await get_user_by_id(order.user_id)
    paid = await get_total_paid(order.id)
    debt = (order.agreed_price - paid) if order.agreed_price else None
    text = (
        f"📦 <b>Buyurtma #{order.id}</b> — {STATUS_LABELS.get(order.status, order.status)}\n\n"
        f"👤 {user.full_name if user else '—'} (@{user.username or '—'})\n"
        f"📐 {order.width_mm}x{order.height_mm}" + (f"x{order.depth_mm}" if order.depth_mm else "") + " mm\n"
        f"📝 {order.description or '—'}\n"
        f"🤖 Taxminiy narx: {order.ai_estimated_price:,} so'm\n".replace(",", " ")
    )
    if order.agreed_price:
        text += f"💰 Kelishilgan: {order.agreed_price:,} so'm\n".replace(",", " ")
        text += f"✅ To'langan: {paid:,} so'm\n".replace(",", " ")
        text += f"⏳ Qarzdorlik: {debt:,} so'm\n".replace(",", " ")
    else:
        text += "💰 Kelishilgan narx hali belgilanmagan\n"
    return text


@router.message(F.text == "📦 Buyurtmalar")
async def list_orders(message: Message):
    orders = await get_all_orders()
    if not orders:
        await message.answer("Hozircha buyurtma yo'q.")
        return
    for order in orders[:15]:
        text = await format_order_text(order)
        await message.answer(text, reply_markup=order_admin_kb(order))


@router.callback_query(F.data.startswith("order_next:"))
async def order_next_status(callback: CallbackQuery, bot: Bot):
    order_id = int(callback.data.split(":")[1])
    order = await get_order(order_id)
    if not order:
        await callback.answer("Topilmadi", show_alert=True)
        return
    next_status = NEXT_STATUS.get(order.status)
    if not next_status:
        await callback.answer("Bu buyurtma allaqachon oxirgi bosqichda", show_alert=True)
        return
    await update_order_status(order_id, next_status)
    order = await get_order(order_id)
    text = await format_order_text(order)
    await callback.message.edit_text(text, reply_markup=order_admin_kb(order))
    await callback.answer("✅ Bosqich yangilandi")

    user = await get_user_by_id(order.user_id)
    try:
        await bot.send_message(
            user.telegram_id,
            f"📦 Buyurtma #{order.id} holati yangilandi: {STATUS_LABELS.get(next_status)}"
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("order_cancel:"))
async def order_cancel(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[1])
    await update_order_status(order_id, "cancelled")
    order = await get_order(order_id)
    text = await format_order_text(order)
    await callback.message.edit_text(text, reply_markup=order_admin_kb(order))
    await callback.answer("Bekor qilindi")


@router.callback_query(F.data.startswith("order_price:"))
async def order_price_start(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split(":")[1])
    await state.update_data(order_id=order_id)
    await state.set_state(SetAgreedPrice.waiting_price)
    await callback.message.answer(f"💰 Buyurtma #{order_id} uchun kelishilgan narxni kiriting (so'mda):\n\n(Bekor qilish uchun /cancel)")
    await callback.answer()


@router.message(SetAgreedPrice.waiting_price)
async def order_price_process(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.clear()
    try:
        price = int(message.text.strip().replace(" ", ""))
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting.", reply_markup=admin_menu_kb())
        return
    order_id = data["order_id"]
    await set_order_agreed_price(order_id, price)
    order = await get_order(order_id)
    await message.answer(f"✅ Narx belgilandi: {price:,} so'm".replace(",", " "), reply_markup=admin_menu_kb())
    user = await get_user_by_id(order.user_id)
    try:
        await bot.send_message(user.telegram_id, f"💰 Buyurtma #{order.id} uchun kelishilgan narx: {price:,} so'm".replace(",", " "))
    except Exception:
        pass


@router.callback_query(F.data.startswith("order_pay:"))
async def order_pay_start(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split(":")[1])
    await state.update_data(order_id=order_id)
    await state.set_state(AddPayment.waiting_amount)
    await callback.message.answer(f"💵 Buyurtma #{order_id} uchun tushgan to'lov summasini kiriting:\n\n(Bekor qilish uchun /cancel)")
    await callback.answer()


@router.message(AddPayment.waiting_amount)
async def order_pay_process(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.clear()
    try:
        amount = int(message.text.strip().replace(" ", ""))
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting.", reply_markup=admin_menu_kb())
        return
    order_id = data["order_id"]
    await add_payment(order_id=order_id, amount=amount)
    paid = await get_total_paid(order_id)
    order = await get_order(order_id)
    await message.answer(f"✅ To'lov qo'shildi: {amount:,} so'm\n💰 Jami to'langan: {paid:,} so'm".replace(",", " "), reply_markup=admin_menu_kb())
    user = await get_user_by_id(order.user_id)
    try:
        await bot.send_message(user.telegram_id, f"✅ Buyurtma #{order.id} bo'yicha {amount:,} so'm to'lov qabul qilindi.".replace(",", " "))
    except Exception:
        pass
