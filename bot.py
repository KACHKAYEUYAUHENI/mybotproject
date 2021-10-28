import sqlite3
import requests
from aiogram import Bot, executor, Dispatcher, types
from config import BOT_TOKEN, OPEN_WEATHER_TOKEN
import aioschedule
import asyncio

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
connect = sqlite3.connect("users_info.db")
cursor = connect.cursor()


@dp.message_handler(commands=["start"])  # start message
async def start_command(message: types.Message):
    await bot.send_message(message.chat.id, f"Привет, напиши город и каждое утро я буду"
                                            f" присылать тебе прогноз погоды")


@dp.message_handler(commands=["unsubscribe"])  # unsubscribe from mailing
async def unsubscription_message(message):
    cursor.execute(f"DELETE FROM users_info WHERE user_id = {message.from_user.id}")
    connect.commit()
    await bot.send_message(message.chat.id, "Вы успешно отписались от рассылки, если захотите "
                                            "возобновить рассылку просто введите город")


@dp.message_handler(content_types=["text"])  # saving and updating in db when the city check is passed
async def subscription_message(message: types.Message):
    user_inormation = [message.from_user.id, message.text]
    try:
        r = requests.get(
            f"http://api.openweathermap.org/data/2.5/weather?q={message.text}&appid={OPEN_WEATHER_TOKEN}&units=metric"
        )
        data = r.json()
        city = data["name"]

        if not (cursor.execute(f"SELECT user_id FROM users_info WHERE user_id = {message.from_user.id}").fetchone()):
            cursor.execute("INSERT INTO users_info VALUES(?,?);", user_inormation)
            connect.commit()
        else:
            cursor.execute("UPDATE users_info SET city = ? WHERE `user_id` = ?;", (message.text, message.from_user.id))
            connect.commit()
        await bot.send_message(message.chat.id, f"Выбран город:{city}")

    except:
        await message.reply("Проверьте название города")


cursor.execute("SELECT * FROM users_info")
j = (cursor.fetchall(),)
data_sql = {}
for i in j:
    data_sql.update(i)


async def send_weather():
    for i in data_sql:
        send_id = i
        city = data_sql[i]

        answers_code = {
            "Clear": "Сегодня ясно \U00002600",
            "Clouds": "Сегодня облачно \U00002601",
            "Rain": "На улице дождь, не забудьте взять зонт \U00002614",
            "Drizzle": "На улице дождь, не забудьте взять зонт \U00002614",
            "Thunderstorm": "На улице гроза, не забудьте взять зонт и будьте осторожны \U000026A1",
            "Snow": "На улице снежно \U0001F328",
            "Mist": "На улице туман, будьте внимательны \U0001F32B"
        }

        r = requests.get(
            f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPEN_WEATHER_TOKEN}&units=metric"
        )
        data = r.json()

        city = data["name"]
        cur_weather = data["main"]["temp"]

        weather_description = data["weather"][0]["main"]
        if weather_description in answers_code:
            wd = answers_code[weather_description]
        else:
            wd = "Оставайтесь дома"

        await bot.send_message(send_id,
                               f"Погода в городе: {city}\nТемпература: {int(cur_weather)}C° {wd}\n"
                               f"Хорошего дня!"
                               )


async def scheduler():
    aioschedule.every().day.at("23:40").do(send_weather)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def on_startup(_):
    asyncio.create_task(scheduler())


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=False, on_startup=on_startup)
