import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import CommandStart, Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database.db_helper import (
    create_dbx,
    save_form,
    get_transferred_fullnames_by_period,
    is_user_blacklisted,
    update_status,
    get_form_by_user_id,
    search_by_fullname,
    search_by_phone,
    get_count_by_period,
    get_total_users,
    get_total_forms,
    get_total_rejected,
    get_total_transferred
)

API_TOKEN = 'ТУТЬ_ТОКЕН_БОТАA'
ADMIN_IDS = [ТУТЬ_ID_АДМИНИСТРАТОРА]  # Мультиадминство

logging.basicConfig(level=logging.DEBUG)

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

def get_admin_form_keyboard(user_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Передан", callback_data=f"mark_transferred:{user_id}")],
        [InlineKeyboardButton(text="🗑 Швырь", callback_data=f"mark_rejected:{user_id}")],
        [InlineKeyboardButton(text="✉️ Ответить", callback_data=f"reply_to_user:{user_id}")],
        [
            InlineKeyboardButton(text="📆 За неделю", callback_data="summary_week"),
            InlineKeyboardButton(text="📅 За месяц", callback_data="summary_month")
        ]
    ])
    return keyboard

def get_admin_control_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Поиск по ФИО", callback_data="search_fullname")],
        [InlineKeyboardButton(text="📱 Поиск по номеру", callback_data="search_phone")],
        [InlineKeyboardButton(text="📅 Список переданных за месяц", callback_data="list_transferred_month")],
        [InlineKeyboardButton(text="📊 Количество переданных за месяц", callback_data="count_transferred_month")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="statistics")]
    ])
    return keyboard

class Form(StatesGroup):
    citizenship = State()
    age = State()
    fullname = State()
    city = State()
    address = State()
    bad_habits = State()
    username = State()
    travel = State()
    license = State()
    phone = State()
    passport = State()
    experience = State()
    passport_front = State()
    passport_back = State()
    selfie = State()

class AdminSearch(StatesGroup):
    waiting_for_fullname = State()
    waiting_for_phone = State()
    waiting_for_reply = State()

async def send_to_admins(text, **kwargs):
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, **kwargs)
        except Exception as e:
            logging.error(f"Ошибка отправки сообщения админу {admin_id}: {e}")

async def send_photo_to_admins(photo, **kwargs):
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_photo(admin_id, photo, **kwargs)
        except Exception as e:
            logging.error(f"Ошибка отправки фото админу {admin_id}: {e}")

@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    logging.debug(f"User ID: {message.from_user.id}")
    if message.from_user.id in ADMIN_IDS:
        await message.answer(
            "👨‍💼 Добро пожаловать, администратор! Выберите действие:",
            reply_markup=get_admin_control_keyboard()
        )
    else:
        # Оповещение всех админов о новом пользователе
        await send_to_admins(
            f"🔔 Новый пользователь: <a href='tg://user?id={message.from_user.id}'>{message.from_user.full_name}</a>\nID: <code>{message.from_user.id}</code>",
            parse_mode=ParseMode.HTML
        )
        if is_user_blacklisted(message.from_user.id):
            warn_text = f"⚠️ Этот питух ранее был помечен как ШВЫРЬ.\nID: <code>{message.from_user.id}</code>"
            await send_to_admins(warn_text)
            await message.answer("⚠️ Ваша анкета будет проверена с особой тщательностью.")
        await message.answer("Добро пожаловать! Ответьте на вопросы ниже.\n\n<b>0. Укажите ваше гражданство:</b>")
        await state.set_state(Form.citizenship)

@dp.message(Form.citizenship)
async def citizenship(message: types.Message, state: FSMContext):
    await state.update_data(citizenship=message.text)
    await message.answer("1. Укажите ваш возраст:")
    await state.set_state(Form.age)

@dp.message(Form.age)
async def age(message: types.Message, state: FSMContext):
    await state.update_data(age=message.text)
    await message.answer("2. Укажите ваше ФИО:")
    await state.set_state(Form.fullname)

@dp.message(Form.fullname)
async def fullname(message: types.Message, state: FSMContext):
    await state.update_data(fullname=message.text)
    await message.answer("3. Город / Адрес прописки:")
    await state.set_state(Form.city)

@dp.message(Form.city)
async def city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("4. Адрес где живете сейчас:")
    await state.set_state(Form.address)

@dp.message(Form.address)
async def address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    await message.answer("5. Вредные привычки?")
    await state.set_state(Form.bad_habits)

@dp.message(Form.bad_habits)
async def habits(message: types.Message, state: FSMContext):
    await state.update_data(bad_habits=message.text)
    await message.answer("6. Ваш username в Telegram:")
    await state.set_state(Form.username)

@dp.message(Form.username)
async def username(message: types.Message, state: FSMContext):
    await state.update_data(username=message.text)
    await message.answer("7. Готовы ли поработать в РФ?")
    await state.set_state(Form.travel)

@dp.message(Form.travel)
async def travel(message: types.Message, state: FSMContext):
    await state.update_data(travel=message.text)
    await message.answer("8. Наличие водительского прав?")
    await state.set_state(Form.license)

@dp.message(Form.license)
async def license(message: types.Message, state: FSMContext):
    await state.update_data(license=message.text)
    await message.answer("9. Ваш номер телефона:")
    await state.set_state(Form.phone)

@dp.message(Form.phone)
async def phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("10. Наличие загранпаспорта?")
    await state.set_state(Form.passport)

@dp.message(Form.passport)
async def passport(message: types.Message, state: FSMContext):
    await state.update_data(passport=message.text)
    await message.answer("11. Опыт работы:")
    await state.set_state(Form.experience)

@dp.message(Form.experience)
async def experience(message: types.Message, state: FSMContext):
    await state.update_data(experience=message.text)
    await message.answer("12. Фото лицевой стороны паспорта:")
    await state.set_state(Form.passport_front)

@dp.message(Form.passport_front, F.photo)
async def front_photo(message: types.Message, state: FSMContext):
    await state.update_data(passport_front=message.photo[-1].file_id)
    data = await state.get_data()
    if "киргиз" in data.get("citizenship", "").lower():
        await message.answer("13. Фото обратной стороны паспорта:")
        await state.set_state(Form.passport_back)
    else:
        await message.answer("14. Селфи с паспортом:")
        await state.set_state(Form.selfie)

@dp.message(Form.passport_back, F.photo)
async def back_photo(message: types.Message, state: FSMContext):
    await state.update_data(passport_back=message.photo[-1].file_id)
    await message.answer("14. Селфи с паспортом:")
    await state.set_state(Form.selfie)

@dp.message(Form.selfie, F.photo)
async def selfie_photo(message: types.Message, state: FSMContext):
    await state.update_data(selfie=message.photo[-1].file_id)
    data = await state.get_data()
    user_id = message.from_user.id

    fullname_link = f'<a href="tg://user?id={user_id}">{data["fullname"]}</a>'
    text = (
        "<b>📋 Кура заполнила анкету:</b>\n\n"
        f"<b>Гражданство:</b> {data['citizenship']}\n"
        f"<b>Возраст:</b> {data['age']}\n"
        f"<b>ФИО:</b> {fullname_link}\n"
        f"<b>Прописан:</b> {data['city']}\n"
        f"<b>Проживает:</b> {data['address']}\n"
        f"<b>Привычки:</b> {data['bad_habits']}\n"
        f"<b>Username:</b> @{data['username']}\n"
        f"<b>Воркать в РФ:</b> {data['travel']}\n"
        f"<b>Права:</b> {data['license']}\n"
        f"<b>Телефон:</b> {data['phone']}\n"
        f"<b>Загранпаспорт:</b> {data['passport']}\n"
        f"<b>Опыт работы:</b> {data['experience']}\n"
    )

    if len(text) > 4000:
        text = f"<b>📋 Новая анкета:</b>\n\n<b>ФИО:</b> {fullname_link}\n<b>User ID:</b> {user_id}"

    keyboard = get_admin_form_keyboard(user_id)
    await send_to_admins(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

    await send_photo_to_admins(data['passport_front'], caption="📄 Лицевая сторона паспорта")
    if 'passport_back' in data:
        await send_photo_to_admins(data['passport_back'], caption="📄 Обратная сторона паспорта")
    await send_photo_to_admins(data['selfie'], caption="🤳 Селфи с паспортом")

    try:
        save_form(data, user_id=user_id)
    except Exception as e:
        logging.error(f"Ошибка сохранения анкеты в БД: {e}")

    await message.answer("✅ Анкета отправлена. Скоро мы свяжемся с вами!")
    await state.clear()

@dp.callback_query()
async def handle_admin_buttons(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Только администратор может использовать эти кнопки.", show_alert=True)
        return

    try:
        if callback.data.startswith("mark_transferred:"):
            form_user_id = int(callback.data.split(":")[1])
            update_status(form_user_id, "передан")
            await callback.answer("📦 Отмечено как переданное")
            form_data = get_form_by_user_id(form_user_id)
            if form_data:
                status_text = (
                    f"<b>📋 Анкета помечена как ПЕРЕДАН:</b>\n\n"
                    f"<b>Гражданство:</b> {form_data.get('citizenship', 'N/A')}\n"
                    f"<b>Возраст:</b> {form_data.get('age', 'N/A')}\n"
                    f"<b>ФИО:</b> <a href=\"tg://user?id={form_user_id}\">{form_data.get('fullname', 'N/A')}</a>\n"
                    f"<b>Прописка:</b> {form_data.get('city', 'N/A')}\n"
                    f"<b>Проживание:</b> {form_data.get('address', 'N/A')}\n"
                    f"<b>Привычки:</b> {form_data.get('bad_habits', 'N/A')}\n"
                    f"<b>Username:</b> @{form_data.get('username', 'N/A')}\n"
                    f"<b>Командировки в РФ:</b> {form_data.get('travel', 'N/A')}\n"
                    f"<b>Права:</b> {form_data.get('license', 'N/A')}\n"
                    f"<b>Телефон:</b> {form_data.get('phone', 'N/A')}\n"
                    f"<b>Загранпаспорт:</b> {form_data.get('passport', 'N/A')}\n"
                    f"<b>Опыт работы:</b> {form_data.get('experience', 'N/A')}"
                )
                await send_to_admins(status_text, parse_mode=ParseMode.HTML)
                if form_data.get('passport_front'):
                    await send_photo_to_admins(form_data['passport_front'], caption="📄 Лицевая сторона паспорта")
                if form_data.get('passport_back') and form_data.get('passport_back') != 'N/A':
                    await send_photo_to_admins(form_data['passport_back'], caption="📄 Обратная сторона паспорта")
                if form_data.get('selfie'):
                    await send_photo_to_admins(form_data['selfie'], caption="🤳 Селфи с паспортом")
            else:
                await send_to_admins(f"⚠️ Анкета для пользователя {form_user_id} не найдена.")

        elif callback.data.startswith("mark_rejected:"):
            form_user_id = int(callback.data.split(":")[1])
            update_status(form_user_id, "швырь")
            await callback.answer("🗑 Отмечено как швырь")
            form_data = get_form_by_user_id(form_user_id)
            if form_data:
                status_text = (
                    f"<b>📋 Анкета помечена как ШВЫРЬ:</b>\n\n"
                    f"<b>Гражданство:</b> {form_data.get('citizenship', 'N/A')}\n"
                    f"<b>Возраст:</b> {form_data.get('age', 'N/A')}\n"
                    f"<b>ФИО:</b> <a href=\"tg://user?id={form_user_id}\">{form_data.get('fullname', 'N/A')}</a>\n"
                    f"<b>Прописка:</b> {form_data.get('city', 'N/A')}\n"
                    f"<b>Проживание:</b> {form_data.get('address', 'N/A')}\n"
                    f"<b>Привычки:</b> {form_data.get('bad_habits', 'N/A')}\n"
                    f"<b>Username:</b> @{form_data.get('username', 'N/A')}\n"
                    f"<b>Командировки в РФ:</b> {form_data.get('travel', 'N/A')}\n"
                    f"<b>Права:</b> {form_data.get('license', 'N/A')}\n"
                    f"<b>Телефон:</b> {form_data.get('phone', 'N/A')}\n"
                    f"<b>Загранпаспорт:</b> {form_data.get('passport', 'N/A')}\n"
                    f"<b>Опыт работы:</b> {form_data.get('experience', 'N/A')}"
                )
                await send_to_admins(status_text, parse_mode=ParseMode.HTML)
                if form_data.get('passport_front'):
                    await send_photo_to_admins(form_data['passport_front'], caption="📄 Лицевая сторона паспорта")
                if form_data.get('passport_back') and form_data.get('passport_back') != 'N/A':
                    await send_photo_to_admins(form_data['passport_back'], caption="📄 Обратная сторона паспорта")
                if form_data.get('selfie'):
                    await send_photo_to_admins(form_data['selfie'], caption="🤳 Селфи с паспортом")
            else:
                await send_to_admins(f"⚠️ Анкета для пользователя {form_user_id} не найдена.")

        elif callback.data.startswith("reply_to_user:"):
            form_user_id = int(callback.data.split(":")[1])
            await state.update_data(reply_user_id=form_user_id)
            await callback.message.answer("Введите текст ответа для пользователя:")
            await state.set_state(AdminSearch.waiting_for_reply)
            await callback.answer()

        elif callback.data == "summary_week":
            fullnames = get_transferred_fullnames_by_period(days=7)
            if fullnames:
                text = "📅 Переданные за неделю:\n" + "\n".join(f"- {item['fullname']} ({item['created_at']})" for item in fullnames)
            else:
                text = "⚠️ За неделю нет переданных анкет."
            await bot.send_message(callback.from_user.id, text)
            await callback.answer("✅ Список отправлен")

        elif callback.data == "summary_month":
            fullnames = get_transferred_fullnames_by_period(days=30)
            if fullnames:
                text = "📅 Переданные за месяц:\n" + "\n".join(f"- {item['fullname']} ({item['created_at']})" for item in fullnames)
            else:
                text = "⚠️ За месяц нет переданных анкет."
            await bot.send_message(callback.from_user.id, text)
            await callback.answer("✅ Список отправлен")

        elif callback.data == "list_transferred_month":
            fullnames = get_transferred_fullnames_by_period(days=30)
            if fullnames:
                text = "📅 Переданные за месяц:\n" + "\n".join(f"- {item['fullname']} ({item['created_at']})" for item in fullnames)
            else:
                text = "⚠️ За месяц нет переданных анкет."
            await bot.send_message(callback.from_user.id, text)
            await callback.answer("✅ Список отправлен")

        elif callback.data == "count_transferred_month":
            count = get_count_by_period(days=30)
            text = f"📊 Количество переданных анкет за месяц: {count}"
            await bot.send_message(callback.from_user.id, text)
            await callback.answer("✅ Количество отправлено")

        elif callback.data == "statistics":
            total_users = get_total_users()
            total_forms = get_total_forms()
            total_rejected = get_total_rejected()
            total_transferred = get_total_transferred()
            text = (f"📊 <b>Статистика бота</b>\n\n"
                    f"👥 Всего пользователей: <b>{total_users}</b>\n"
                    f"📋 Заполнено анкет: <b>{total_forms}</b>\n"
                    f"🗑 Швырей: <b>{total_rejected}</b>\n"
                    f"✅ Переданных: <b>{total_transferred}</b>")
            await bot.send_message(callback.from_user.id, text, parse_mode=ParseMode.HTML)
            await callback.answer()

        elif callback.data == "search_fullname":
            await callback.message.answer("Введите ФИО для поиска:")
            await state.set_state(AdminSearch.waiting_for_fullname)
            await callback.answer()

        elif callback.data == "search_phone":
            await callback.message.answer("Введите номер телефона для поиска:")
            await state.set_state(AdminSearch.waiting_for_phone)
            await callback.answer()

    except Exception as e:
        logging.error(f"Ошибка в callback: {e}")
        await callback.answer("❌ Произошла ошибка при обработке.", show_alert=True)

@dp.message(AdminSearch.waiting_for_reply)
async def admin_reply_to_user(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("reply_user_id")
    if user_id:
        try:
            await bot.send_message(user_id, f"💬 Ответ от администратора:\n\n{message.text}")
            await send_to_admins(f"✅ Сообщение отправлено пользователю с ID {user_id}")
        except Exception as e:
            await message.answer(f"❌ Ошибка отправки: {e}")
    else:
        await message.answer("❌ Ошибка: не найден ID пользователя для ответа.")
    await state.clear()

@dp.message(AdminSearch.waiting_for_fullname)
async def process_search_fullname(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Только администратор может выполнять поиск.")
        return
    fullname = message.text.strip()
    try:
        results = search_by_fullname(fullname)
        if not results:
            await message.answer(f"⚠️ Анкеты с ФИО '{fullname}' не найдены.")
        else:
            for form in results:
                text = (
                    f"<b>📋 Анкета:</b>\n\n"
                    f"<b>Гражданство:</b> {form.get('citizenship', 'N/A')}\n"
                    f"<b>Возраст:</b> {form.get('age', 'N/A')}\n"
                    f"<b>ФИО:</b> <a href='tg://user?id={form.get('user_id', '')}'>{form.get('fullname', 'N/A')}</a>\n"
                    f"<b>Прописка:</b> {form.get('city', 'N/A')}\n"
                    f"<b>Проживание:</b> {form.get('address', 'N/A')}\n"
                    f"<b>Привычки:</b> {form.get('bad_habits', 'N/A')}\n"
                    f"<b>Username:</b> @{form.get('username', 'N/A')}\n"
                    f"<b>Командировки в РФ:</b> {form.get('travel', 'N/A')}\n"
                    f"<b>Права:</b> {form.get('license', 'N/A')}\n"
                    f"<b>Телефон:</b> {form.get('phone', 'N/A')}\n"
                    f"<b>Загранпаспорт:</b> {form.get('passport', 'N/A')}\n"
                    f"<b>Опыт работы:</b> {form.get('experience', 'N/A')}\n"
                    f"<b>Статус:</b> {form.get('status', 'N/A')}\n"
                    f"<b>Дата создания:</b> {form.get('created_at', 'N/A')}\n"
                )
                await message.answer(text, parse_mode=ParseMode.HTML)
                if form.get('passport_front'):
                    await bot.send_photo(message.from_user.id, form['passport_front'], caption="📄 Лицевая сторона паспорта")
                if form.get('passport_back') and form.get('passport_back') != 'N/A':
                    await bot.send_photo(message.from_user.id, form['passport_back'], caption="📄 Обратная сторона паспорта")
                if form.get('selfie'):
                    await bot.send_photo(message.from_user.id, form['selfie'], caption="🤳 Селфи с паспортом")
        await state.clear()
    except Exception as e:
        logging.error(f"Error searching by fullname: {e}")
        await message.answer("❌ Ошибка при поиске. Попробуйте снова.")
        await state.clear()

@dp.message(AdminSearch.waiting_for_phone)
async def process_search_phone(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Только администратор может выполнять поиск.")
        return
    phone = message.text.strip()
    try:
        results = search_by_phone(phone)
        if not results:
            await message.answer(f"⚠️ Анкеты с номером телефона '{phone}' не найдены.")
        else:
            for form in results:
                text = (
                    f"<b>📋 Анкета:</b>\n\n"
                    f"<b>Гражданство:</b> {form.get('citizenship', 'N/A')}\n"
                    f"<b>Возраст:</b> {form.get('age', 'N/A')}\n"
                    f"<b>ФИО:</b> <a href='tg://user?id={form.get('user_id', '')}'>{form.get('fullname', 'N/A')}</a>\n"
                    f"<b>Прописка:</b> {form.get('city', 'N/A')}\n"
                    f"<b>Проживание:</b> {form.get('address', 'N/A')}\n"
                    f"<b>Привычки:</b> {form.get('bad_habits', 'N/A')}\n"
                    f"<b>Username:</b> @{form.get('username', 'N/A')}\n"
                    f"<b>Командировки в РФ:</b> {form.get('travel', 'N/A')}\n"
                    f"<b>Права:</b> {form.get('license', 'N/A')}\n"
                    f"<b>Телефон:</b> {form.get('phone', 'N/A')}\n"
                    f"<b>Загранпаспорт:</b> {form.get('passport', 'N/A')}\n"
                    f"<b>Опыт работы:</b> {form.get('experience', 'N/A')}\n"
                    f"<b>Статус:</b> {form.get('status', 'N/A')}\n"
                    f"<b>Дата создания:</b> {form.get('created_at', 'N/A')}\n"
                )
                await message.answer(text, parse_mode=ParseMode.HTML)
                if form.get('passport_front'):
                    await bot.send_photo(message.from_user.id, form['passport_front'], caption="📄 Лицевая сторона паспорта")
                if form.get('passport_back') and form.get('passport_back') != 'N/A':
                    await bot.send_photo(message.from_user.id, form['passport_back'], caption="📄 Обратная сторона паспорта")
                if form.get('selfie'):
                    await bot.send_photo(message.from_user.id, form['selfie'], caption="🤳 Селфи с паспортом")
        await state.clear()
    except Exception as e:
        logging.error(f"Error searching by phone: {e}")
        await message.answer("❌ Ошибка при поиске. Попробуйте снова.")
        await state.clear()

async def main():
    try:
        create_dbx()
        logging.debug("Database initialized")
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Error in main loop: {e}")

if __name__ == "__main__":
    asyncio.run(main())