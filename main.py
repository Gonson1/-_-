import telebot
from telebot import types
import time
from datetime import datetime, timedelta
import json
from threading import Thread
from collections import defaultdict

# Загружаем расписание из файла
def load_schedules():
    with open('schedules.json', 'r', encoding='utf-8') as f:
        return json.load(f)


# Загружаем расписание в переменную
schedules = load_schedules()

# Укажите свой токен Telegram-бота
bot = telebot.TeleBot('7531499134:AAHVFuV9h7-JpuCKSs20ImQpPJxQAOH3mKw')

# Главное меню
main_menu = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
main_menu.add(types.KeyboardButton("📅 Расписание"))
main_menu.add(types.KeyboardButton("👤 Профиль"))

# Переменные для отслеживания состояния
user_state = {}
selected_group = {}
selected_week = {}
notifications = defaultdict(dict)  # Хранение времени уведомлений для пользователей


# Функция проверки уведомлений
def notification_checker():
    while True:
        current_time = datetime.now().strftime("%H:%M")
        for user_id, lessons in list(notifications.items()):
            for lesson, notify_time in list(lessons.items()):
                if notify_time == current_time:
                    bot.send_message(user_id, f"Напоминание: скоро начнется занятие *{lesson}*", parse_mode="Markdown")
                    del lessons[lesson]
        time.sleep(30)


# Обработка команды /start
@bot.message_handler(commands=['start'])
def start(message):
    user_state[message.chat.id] = {"step": "menu"}
    bot.send_message(
        message.chat.id,
        "Привет, я твой бот, который будет напоминать о начале занятий!",
        reply_markup=main_menu
    )


# Обработка кнопки "📅 Расписание"
@bot.message_handler(func=lambda msg: msg.text == "📅 Расписание")
def choose_week(message):
    user_state[message.chat.id] = {"step": "week"}
    week_markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    week_markup.add(
        types.KeyboardButton("Текущая неделя (16)"),
        types.KeyboardButton("Следующая неделя (17)"),
        types.KeyboardButton("🔙 Назад")
    )
    bot.send_message(message.chat.id, "Выберите неделю:", reply_markup=week_markup)


# Обработка выбора недели
@bot.message_handler(func=lambda msg: msg.text in ["Текущая неделя (16)", "Следующая неделя (17)"])
def choose_group(message):
    week = "16" if "Текущая" in message.text else "17"
    selected_week[message.chat.id] = week
    user_state[message.chat.id] = {"step": "group", "week": week}

    group_markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for group in schedules[week].keys():
        group_markup.add(types.KeyboardButton(group))
    group_markup.add(types.KeyboardButton("🔙 Назад"))

    bot.send_message(
        message.chat.id,
        f"Вы выбрали {message.text}. Теперь выберите группу:",
        reply_markup=group_markup
    )


@bot.message_handler(
    func=lambda msg: msg.chat.id in selected_week and msg.text in schedules[selected_week[msg.chat.id]].keys())
def choose_day(message):
    group = message.text
    week = selected_week[message.chat.id]
    selected_group[message.chat.id] = group
    user_state[message.chat.id] = {"step": "day", "group": group, "week": week}

    days_markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for day in schedules[week][group].keys():
        days_markup.add(types.KeyboardButton(day))
    days_markup.add(types.KeyboardButton("🔙 Назад"))
    days_markup.add(types.KeyboardButton("🔔 Напоминания на всю неделю"))  # Добавляем кнопку

    bot.send_message(
        message.chat.id,
        f"Вы выбрали группу {group}. Теперь выберите день недели или установите напоминания на всю неделю:",
        reply_markup=days_markup
    )


# Обработка кнопки "🔔 Напоминания на всю неделю"
@bot.message_handler(func=lambda msg: msg.text == "🔔 Напоминания на всю неделю")
def set_week_notifications(message):
    group = selected_group[message.chat.id]
    week = selected_week[message.chat.id]
    user_notifications = []

    # Проходим по всем дням и занятиям
    for day, lessons in schedules[week][group].items():
        for lesson_name, lesson_details in lessons.items():
            lesson_time = datetime.strptime(lesson_details['time'], "%H:%M")
            notify_time = (lesson_time - timedelta(minutes=15)).strftime("%H:%M")  # Уведомление за 15 минут
            notifications[message.chat.id][lesson_name] = notify_time
            user_notifications.append(f"{lesson_name} ({day}) - {notify_time}")

    # Сообщение о добавленных напоминаниях
    if user_notifications:
        bot.send_message(
            message.chat.id,
            "Напоминания установлены для следующих занятий:\n" + "\n".join(user_notifications),
            parse_mode="Markdown"
        )
    else:
        bot.send_message(message.chat.id, "Не удалось установить напоминания. Проверьте расписание.")

    # Возвращаем пользователя в главное меню
    user_state[message.chat.id] = {"step": "menu"}
    bot.send_message(message.chat.id, "Вы вернулись в главное меню.", reply_markup=main_menu)


# Обработка выбора дня недели
@bot.message_handler(
    func=lambda msg: msg.chat.id in selected_group and msg.text in schedules[selected_week[msg.chat.id]][
        selected_group[msg.chat.id]])
def show_day_schedule(message):
    group = selected_group[message.chat.id]
    week = selected_week[message.chat.id]
    day = message.text
    user_state[message.chat.id] = {"step": "lesson", "group": group, "week": week, "day": day}

    lessons_markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for lesson in schedules[week][group][day]:
        lessons_markup.add(types.KeyboardButton(lesson))
    lessons_markup.add(types.KeyboardButton("🔙 Назад"))
    lessons_markup.add(types.KeyboardButton("🔔 Напоминания на все занятия дня"))  # Добавляем кнопку

    bot.send_message(message.chat.id, f"Выберите занятие в {day}, либо установите напоминания на все занятия этого дня:",
                     reply_markup=lessons_markup)


# Обработка кнопки "🔔 Напоминания на все занятия дня"
@bot.message_handler(func=lambda msg: msg.text == "🔔 Напоминания на все занятия дня")
def set_day_notifications(message):
    group = selected_group[message.chat.id]
    week = selected_week[message.chat.id]
    day = user_state[message.chat.id]["day"]
    user_notifications = []

    # Проходим по всем занятиям в выбранный день
    for lesson_name, lesson_details in schedules[week][group][day].items():
        lesson_time = datetime.strptime(lesson_details['time'], "%H:%M")
        notify_time = (lesson_time - timedelta(minutes=15)).strftime("%H:%M")  # Уведомление за 15 минут
        notifications[message.chat.id][lesson_name] = notify_time
        user_notifications.append(f"{lesson_name} - {notify_time}")

    # Сообщение о добавленных напоминаниях
    if user_notifications:
        bot.send_message(
            message.chat.id,
            f"Напоминания установлены для занятий в {day}:\n" + "\n".join(user_notifications),
            parse_mode="Markdown"
        )
    else:
        bot.send_message(message.chat.id, "Не удалось установить напоминания. Проверьте расписание.")
# Возвращаем пользователя в главное меню
    user_state[message.chat.id] = {"step": "menu"}
    bot.send_message(message.chat.id, "Вы вернулись в главное меню.", reply_markup=main_menu)

# Обработка выбора занятия
@bot.message_handler(func=lambda msg: msg.chat.id in selected_group and any(
    msg.text in lessons for lessons in schedules[selected_week[msg.chat.id]][selected_group[msg.chat.id]].values()
))
def set_notification(message):
    group = selected_group[message.chat.id]
    week = selected_week[message.chat.id]
    day = user_state[message.chat.id]["day"]
    lesson_name = message.text
    lesson = schedules[week][group][day][lesson_name]

    # Сохраняем выбранное занятие в состоянии
    user_state[message.chat.id] = {
        "step": "notification",
        "lesson": lesson_name,
        "lesson_time": lesson['time'],
        "lesson_details": lesson
    }

    # Убираем клавиатуру, оставляя только текст
    bot.send_message(
        message.chat.id,
        f"Вы выбрали занятие: *{lesson_name}*\n"
        f"Время: {lesson['time']}\n"
        f"Подгруппа: {lesson.get('subgroup', 'Не указана')}\n"
        f"Аудитория: {lesson.get('auditory', 'Не указана')}\n"
        f"Укажите время для напоминания (например, 15 минут до начала занятия):",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove()  # Удаляем кнопки
    )

# Установка времени напоминания
@bot.message_handler(func=lambda msg: user_state.get(msg.chat.id, {}).get("step") == "notification")
def handle_reminder(message):
    try:
        reminder_minutes = int(message.text.split()[0])  # Читаем первое число (например, "15")
        lesson_time = datetime.strptime(user_state[message.chat.id]["lesson_time"], "%H:%M")
        notify_time = (lesson_time - timedelta(minutes=reminder_minutes)).strftime("%H:%M")
        lesson = user_state[message.chat.id]["lesson"]

        # Сохраняем напоминание
        notifications[message.chat.id][lesson] = notify_time

        bot.send_message(message.chat.id, f"Напоминание для занятия *{lesson}* установлено на {notify_time}.",
                         parse_mode="Markdown")

        # Переход в главное меню после установки напоминания
        user_state[message.chat.id] = {"step": "menu"}
        bot.send_message(message.chat.id, "Вы вернулись в главное меню.", reply_markup=main_menu)
    except ValueError:
        bot.send_message(message.chat.id, "Введите корректное число минут (например, 15).")

import html

# Обработка кнопки "👤 Профиль"
# Показ профиля с кнопками для удаления напоминаний
@bot.message_handler(func=lambda msg: msg.text == "👤 Профиль")
def show_profile(message):
    user_notifications = notifications.get(message.chat.id, {})

    if user_notifications:
        profile_text = "Ваши напоминания:\n\n"
        buttons = types.InlineKeyboardMarkup(row_width=1)

        for lesson, notify_time in user_notifications.items():
            profile_text += f"📘 Занятие: <b>{lesson}</b>\n🕒 Время напоминания: {notify_time}\n\n"
            # Кнопка для удаления
            buttons.add(
                types.InlineKeyboardButton(
                    text=f"Удалить: {lesson}",
                    callback_data=f"delete_{lesson}"  # Оставляем данные как есть
                )
            )
    else:
        profile_text = "У вас нет установленных напоминаний."
        buttons = None

    # Кнопка "🔙 Назад" для возврата в главное меню
    back_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    back_markup.add(types.KeyboardButton("🔙 Назад"))

    bot.send_message(
        message.chat.id,
        profile_text,
        reply_markup=back_markup,
        parse_mode="HTML",
    )
    if buttons:
        bot.send_message(
            message.chat.id,
            "Выберите напоминание для удаления:",
            reply_markup=buttons
        )


# Обработка нажатия кнопки удаления напоминания
@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_"))
def handle_delete_reminder(call):
    lesson_to_delete = call.data.split("delete_")[1]  # Извлекаем название занятия
    user_id = call.message.chat.id

    # Убедимся, что название занятия в notifications не изменено
    if user_id in notifications and lesson_to_delete in notifications[user_id]:
        del notifications[user_id][lesson_to_delete]
        bot.answer_callback_query(call.id, f"Напоминание для '{lesson_to_delete}' удалено.")
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"Напоминание для занятия <b>{lesson_to_delete}</b> успешно удалено.",
            parse_mode="HTML"
        )
    else:
        bot.answer_callback_query(call.id, "Напоминание не найдено.")

    # Обновляем профиль
    show_profile(call.message)

# Удаление напоминания
@bot.message_handler(func=lambda msg: msg.text.startswith('/delete_'))
def delete_reminder(message):
    lesson_to_delete = message.text.split('_', 1)[1]  # Получаем название занятия
    user_id = message.chat.id

    # Удаляем напоминание для выбранного занятия
    if user_id in notifications and lesson_to_delete in notifications[user_id]:
        del notifications[user_id][lesson_to_delete]
        bot.send_message(user_id, f"Напоминание для занятия <b>{lesson_to_delete}</b> было удалено.", parse_mode="HTML")

        # Возвращаем в профиль
        show_profile(message)
    else:
        bot.send_message(user_id, f"Напоминание для занятия <b>{lesson_to_delete}</b> не найдено.", parse_mode="HTML")


# Обработка кнопки "🔙 Назад" для всех шагов, включая профиль
@bot.message_handler(func=lambda msg: msg.text == "🔙 Назад")
def go_back(message):
    current_state = user_state.get(message.chat.id, {})

    if current_state.get("step") == "notification":
        # Если на шаге напоминания, возвращаем на выбор занятия
        group = selected_group[message.chat.id]
        week = selected_week[message.chat.id]
        day = user_state[message.chat.id]["day"]

        lessons_markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        for lesson in schedules[week][group][day]:
            lessons_markup.add(types.KeyboardButton(lesson))
        lessons_markup.add(types.KeyboardButton("🔙 Назад"))

        bot.send_message(message.chat.id, f"Выберите занятие в {day}:", reply_markup=lessons_markup)

        # Сбрасываем состояние, чтобы вернуться на выбор занятия
        user_state[message.chat.id] = {"step": "lesson", "group": group, "week": week, "day": day}
    elif current_state.get("step") == "lesson":
        # Если на шаге выбора занятия, возвращаем на выбор дня
        group = selected_group[message.chat.id]
        week = selected_week[message.chat.id]
        day = user_state[message.chat.id]["day"]

        days_markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        for day_option in schedules[week][group].keys():
            days_markup.add(types.KeyboardButton(day_option))
        days_markup.add(types.KeyboardButton("🔙 Назад"))

        bot.send_message(message.chat.id, f"Выберите день недели:", reply_markup=days_markup)

        # Сбрасываем состояние, чтобы вернуться на выбор дня
        user_state[message.chat.id] = {"step": "day", "group": group, "week": week}
    elif current_state.get("step") == "day":
        # Если на шаге выбора дня, возвращаем на выбор группы
        group = selected_group[message.chat.id]
        week = selected_week[message.chat.id]

        group_markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        for group_option in schedules[week].keys():
            group_markup.add(types.KeyboardButton(group_option))
        group_markup.add(types.KeyboardButton("🔙 Назад"))

        bot.send_message(message.chat.id, f"Выберите группу:", reply_markup=group_markup)

        # Сбрасываем состояние, чтобы вернуться на выбор группы
        user_state[message.chat.id] = {"step": "group", "week": week}
    elif current_state.get("step") == "group":
        # Если на шаге выбора группы, возвращаем на выбор недели
        week_markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        week_markup.add(
            types.KeyboardButton("Текущая неделя (16)"),
            types.KeyboardButton("Следующая неделя (17)"),
            types.KeyboardButton("🔙 Назад")
        )
        bot.send_message(message.chat.id, f"Выберите неделю:", reply_markup=week_markup)

        # Сбрасываем состояние, чтобы вернуться на выбор недели
        user_state[message.chat.id] = {"step": "week"}
    else:
        # Если на другом шаге, просто возвращаем в меню
        user_state[message.chat.id] = {"step": "menu"}
        bot.send_message(message.chat.id, "Вы вернулись в главное меню.", reply_markup=main_menu)

# Запуск проверки уведомлений
thread = Thread(target=notification_checker, daemon=True)
thread.start()

# Запуск бота
bot.polling(none_stop=True)
