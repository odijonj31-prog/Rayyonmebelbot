from datetime import datetime
from sqlalchemy import select, update, delete, func
from database.db import async_session
from database.models import User, Admin, Channel, PortfolioItem, MaterialOption, Order, Payment, Setting


# ---------- USERS ----------

async def get_or_create_user(telegram_id: int, username: str | None, full_name: str | None) -> User:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user:
            return user
        user = User(telegram_id=telegram_id, username=username, full_name=full_name)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def get_user(telegram_id: int) -> User | None:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()


async def get_user_by_id(user_id: int) -> User | None:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()


async def set_user_phone(telegram_id: int, phone: str):
    async with async_session() as session:
        await session.execute(update(User).where(User.telegram_id == telegram_id).values(phone=phone))
        await session.commit()


async def count_users() -> int:
    async with async_session() as session:
        result = await session.execute(select(func.count()).select_from(User))
        return result.scalar_one()


async def get_all_user_ids() -> list[int]:
    async with async_session() as session:
        result = await session.execute(select(User.telegram_id))
        return [row[0] for row in result.all()]


# ---------- ADMINS ----------

async def is_admin(telegram_id: int) -> bool:
    async with async_session() as session:
        result = await session.execute(select(Admin).where(Admin.telegram_id == telegram_id))
        return result.scalar_one_or_none() is not None


async def add_admin(telegram_id: int):
    async with async_session() as session:
        session.add(Admin(telegram_id=telegram_id))
        await session.commit()


# ---------- CHANNELS (majburiy obuna) ----------

async def add_channel(chat_id: int, title: str, username: str | None, invite_link: str | None) -> Channel:
    async with async_session() as session:
        ch = Channel(chat_id=chat_id, title=title, username=username, invite_link=invite_link)
        session.add(ch)
        await session.commit()
        await session.refresh(ch)
        return ch


async def get_active_channels() -> list[Channel]:
    async with async_session() as session:
        result = await session.execute(select(Channel).where(Channel.is_active == True))
        return list(result.scalars().all())


async def remove_channel(channel_id: int):
    async with async_session() as session:
        await session.execute(delete(Channel).where(Channel.id == channel_id))
        await session.commit()


async def toggle_channel(channel_id: int, active: bool):
    async with async_session() as session:
        await session.execute(update(Channel).where(Channel.id == channel_id).values(is_active=active))
        await session.commit()


# ---------- PORTFOLIO (ishlar katalogi) ----------

async def add_portfolio_item(title: str, photo_file_id: str, description: str | None = None,
                              style_tags: str | None = None) -> PortfolioItem:
    async with async_session() as session:
        item = PortfolioItem(title=title, photo_file_id=photo_file_id, description=description,
                              style_tags=style_tags)
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return item


async def get_active_portfolio() -> list[PortfolioItem]:
    async with async_session() as session:
        result = await session.execute(
            select(PortfolioItem).where(PortfolioItem.is_active == True).order_by(PortfolioItem.added_at.desc())
        )
        return list(result.scalars().all())


async def get_portfolio_item(item_id: int) -> PortfolioItem | None:
    async with async_session() as session:
        result = await session.execute(select(PortfolioItem).where(PortfolioItem.id == item_id))
        return result.scalar_one_or_none()


async def delete_portfolio_item(item_id: int) -> bool:
    async with async_session() as session:
        result = await session.execute(delete(PortfolioItem).where(PortfolioItem.id == item_id))
        await session.commit()
        return result.rowcount > 0


# ---------- MATERIAL OPTIONS (xomashyo/rang/zapchast narxlari) ----------

async def add_material_option(category: str, name: str, extra_price: int) -> MaterialOption:
    async with async_session() as session:
        opt = MaterialOption(category=category, name=name, extra_price=extra_price)
        session.add(opt)
        await session.commit()
        await session.refresh(opt)
        return opt


async def add_materials_bulk(category: str, lines: list[str]) -> int:
    """
    Har bir qator "Nomi - narx" yoki "Nomi-narx" formatida bo'ladi.
    Nechta muvaffaqiyatli qo'shilganini qaytaradi.
    """
    added = 0
    async with async_session() as session:
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if "-" not in line:
                continue
            name_part, price_part = line.rsplit("-", 1)
            name_part = name_part.strip()
            price_part = price_part.strip().replace(" ", "").replace("so'm", "").replace("сум", "")
            if not name_part or not price_part.isdigit():
                continue
            session.add(MaterialOption(category=category, name=name_part, extra_price=int(price_part)))
            added += 1
        await session.commit()
    return added


async def get_active_options(category: str | None = None) -> list[MaterialOption]:
    async with async_session() as session:
        query = select(MaterialOption).where(MaterialOption.is_active == True)
        if category:
            query = query.where(MaterialOption.category == category)
        result = await session.execute(query)
        return list(result.scalars().all())


async def get_options_by_ids(ids: list[int]) -> list[MaterialOption]:
    if not ids:
        return []
    async with async_session() as session:
        result = await session.execute(select(MaterialOption).where(MaterialOption.id.in_(ids)))
        return list(result.scalars().all())


async def delete_material_option(option_id: int) -> bool:
    async with async_session() as session:
        result = await session.execute(delete(MaterialOption).where(MaterialOption.id == option_id))
        await session.commit()
        return result.rowcount > 0


# ---------- ORDERS ----------

async def create_order(user_id: int, width_mm: int | None, height_mm: int | None, depth_mm: int | None,
                        selected_option_ids: list[int], ai_estimated_price: int | None,
                        description: str | None = None, portfolio_item_id: int | None = None,
                        contact_name: str | None = None, contact_phone: str | None = None) -> Order:
    async with async_session() as session:
        order = Order(
            user_id=user_id, width_mm=width_mm, height_mm=height_mm, depth_mm=depth_mm,
            selected_option_ids=selected_option_ids, ai_estimated_price=ai_estimated_price,
            description=description, portfolio_item_id=portfolio_item_id,
            contact_name=contact_name, contact_phone=contact_phone,
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)
        return order


async def get_order(order_id: int) -> Order | None:
    async with async_session() as session:
        result = await session.execute(select(Order).where(Order.id == order_id))
        return result.scalar_one_or_none()


async def get_orders_by_user(user_id: int) -> list[Order]:
    async with async_session() as session:
        result = await session.execute(
            select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc())
        )
        return list(result.scalars().all())


async def get_all_orders(status: str | None = None) -> list[Order]:
    async with async_session() as session:
        query = select(Order).order_by(Order.created_at.desc())
        if status:
            query = query.where(Order.status == status)
        result = await session.execute(query)
        return list(result.scalars().all())


async def update_order_status(order_id: int, status: str):
    async with async_session() as session:
        await session.execute(update(Order).where(Order.id == order_id).values(status=status))
        await session.commit()


async def set_order_agreed_price(order_id: int, price: int):
    async with async_session() as session:
        await session.execute(update(Order).where(Order.id == order_id).values(agreed_price=price))
        await session.commit()


async def count_orders() -> int:
    async with async_session() as session:
        result = await session.execute(select(func.count()).select_from(Order))
        return result.scalar_one()


# ---------- PAYMENTS ----------

async def add_payment(order_id: int, amount: int, note: str | None = None) -> Payment:
    async with async_session() as session:
        payment = Payment(order_id=order_id, amount=amount, note=note)
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
        return payment


async def get_payments_for_order(order_id: int) -> list[Payment]:
    async with async_session() as session:
        result = await session.execute(
            select(Payment).where(Payment.order_id == order_id).order_by(Payment.created_at)
        )
        return list(result.scalars().all())


async def get_total_paid(order_id: int) -> int:
    payments = await get_payments_for_order(order_id)
    return sum(p.amount for p in payments)


# ---------- SETTINGS ----------

async def get_setting(key: str, default: str | None = None) -> str | None:
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == key))
        row = result.scalar_one_or_none()
        return row.value if row else default


async def set_setting(key: str, value: str):
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == key))
        row = result.scalar_one_or_none()
        if row:
            row.value = value
        else:
            session.add(Setting(key=key, value=value))
        await session.commit()


# ---------- ORDER + TO'LOV BIRGALIKDA (mijoz/admin uchun) ----------

async def get_orders_with_payments(user_id: int) -> list[dict]:
    orders = await get_orders_by_user(user_id)
    result = []
    for order in orders:
        paid = await get_total_paid(order.id)
        debt = (order.agreed_price - paid) if order.agreed_price else None
        result.append({"order": order, "paid": paid, "debt": debt})
    return result


async def get_order_with_payment(order_id: int) -> dict | None:
    order = await get_order(order_id)
    if not order:
        return None
    paid = await get_total_paid(order.id)
    debt = (order.agreed_price - paid) if order.agreed_price else None
    return {"order": order, "paid": paid, "debt": debt}
