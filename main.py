from credentials import bot_token, admin_id
import telebot
from telebot import types
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from credentials import bot_token, admin_id
import telebot
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from hashlib import sha256

bot = telebot.TeleBot(bot_token)

# texts
BTN_LIGHT = "💡 por suerte"
BTN_BLACKOUT = "🕯 tronco 'e apagón"
BTN_LOCATION = "AQUIIIIIIII"
BTN_MAP = "A ver el mapa"

MSG_QUERRY = "Tonce... tienes corriente?"
MSG_SHARE_LOCATION = "¿Dónde tú estás?"
MSG_NO_LIGHT = "Qué país 🤬!"
MSG_YES_LIGHT = "Aprovecha"
MSG_START_DISCLAIMER = '<em>¿Es seguro que mande mi ubicación?</em>\n\nEl bot pide la ubicación para poder localizar al usuario en el mapa con su actual estado de corriente eléctrica. Para que cada usuario aparezca una sola vez en el mapa, es necesario guaradar la localización con alguna información que identifique únicamente al usuario. Esta información es el <code>id</code> de Telegram que es único para cada usuario, sin embargo, con este dato se podría obtener información del usuario, por lo que, en lugar de usar el <code>id</code> se utiliza un hash <code>sha256</code> de este número. <a href="https://es.wikipedia.org/wiki/SHA-2">SHA-256</a> es parte de una familia de funciones de hash criptográficas que convierten la entrada en una única salida y es imposible con esa salida obtener cuál fue la entrada. Es por esto que, si alguien obtuviese la información que guarda el bot, para saber la información de los usuarios, tendría que aplicar <code>sha256</code> uno por uno a todos los posibles <code>id</code> de los 400 millones de usuarios en Telegram hasta encontrar el que sea igual al que se guarda en la base de datos. Incluso en este ya muy poco probable caso, las opciones de privacidad de Telegram permiten que (si se activa la opción) ningún usuario que no sea contacto pueda encontrarnos en Telegram.\n\nMUY LARGO; NO LEÍ\nNo hay lío, to\' está fresa.'

FILE_ELPIDIO_AQUI_ID = (
    "BAACAgEAAxkBAAMtYUq0MIh3iZ6lg37OsceYFHE3FvEAAhcCAAIeZFFGjiAeyxCyHcwhBA"
)

# store data
users_db = {}


def read_db():
    global users_db
    with open("users.db", "r") as file:
        users_db = eval(file.read())


def save_db():
    global users_db
    with open("users.db", "w") as file:
        file.write(str(users_db))


@bot.message_handler(commands=["start"])
def handle_start(message):
    # keyboard
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    hashed_id = sha256(str.encode(str(message.from_user.id))).hexdigest()
    if hashed_id in users_db:
        m.row(types.KeyboardButton(BTN_LIGHT), types.KeyboardButton(BTN_BLACKOUT))
    m.row(types.KeyboardButton(BTN_LOCATION, request_location=True))

    bot.send_video(message.chat.id, FILE_ELPIDIO_AQUI_ID)
    bot.send_message(
        message.chat.id,
        MSG_SHARE_LOCATION,
        reply_markup=m,
        allow_sending_without_reply=True,
    )

    bot.send_message(
        message.chat.id,
        MSG_START_DISCLAIMER,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


@bot.message_handler(commands=["logxxx"])
def handle_logxxx(message):
    bot.send_message(admin_id, str(users_db))


@bot.message_handler(commands=["set_users_db"])
def handle_set(message):
    if message.from_user.id != admin_id:
        return
    digest = message.text[14:]
    global users_db
    users_db = eval(digest)


@bot.message_handler(content_types=["location"])
def handdle_location(message):
    print(message.location)
    hashed_id = sha256(str.encode(str(message.from_user.id))).hexdigest()
    users_db[hashed_id] = {
        "location": [message.location.latitude, message.location.longitude],
        "light": True,
    }

    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.row(types.KeyboardButton(BTN_LIGHT), types.KeyboardButton(BTN_BLACKOUT))
    m.row(types.KeyboardButton(BTN_MAP))
    bot.send_message(message.chat.id, MSG_QUERRY, reply_markup=m)

    save_db()


def create_plot():
    # map
    m = gpd.read_file("cuba.geojson")
    cities = pd.read_csv("cu.csv")

    # Plot
    fig, ax = plt.subplots(1)

    ax.set_aspect("equal")

    # m.plot(ax = ax, color='#bde2f2')
    m.plot(ax=ax, color="#d4d4d4")

    img_black = plt.imread("black.png")
    imgblack_box = OffsetImage(img_black, zoom=0.01)

    img_blue = plt.imread("blue.png")
    imgblue_box = OffsetImage(img_blue, zoom=0.01)

    for idx, x in cities.iterrows():
        ax.scatter(x.lng, x.lat, s=0.3, marker="o", color="#ebedda", linewidths=0)
        if x.capital == "primary" or x.capital == "admin":
            ax.text(
                x.lng,
                x.lat,
                x.city,
                fontsize=4,
                horizontalalignment="center",
                color="#222222",
                fontstyle="italic",
            )

    ncases = 0
    apagones = 0
    for user in users_db:
        loc = users_db[user]["location"]
        if loc[1] > -86 and loc[1] < -75.5 and loc[0] > 19.5 and loc[0] < 23.5:
            ncases += 1
            if not users_db[user]["light"]:
                apagones += 1
            ax.add_artist(
                AnnotationBbox(
                    imgblue_box if users_db[user]["light"] == True else imgblack_box,
                    [loc[1] + 0.005, loc[0] + 0.168],
                    frameon=False,
                )
            )

    ax.text(-85, 20.2, f"Cantidad de reportes: {ncases}", fontsize=6)
    ax.text(-85, 19.9, f"Apagones: {apagones}", fontsize=6)

    # fig.set_facecolor('#aaaaaa')
    ax.axis("off")
    plt.savefig("image.png", bbox_inches="tight", dpi=600)

    plt.close()


@bot.message_handler(content_types=["text"])
def handle_text_messages(message):
    hashed_id = sha256(str.encode(str(message.from_user.id))).hexdigest()
    if not hashed_id in users_db:
        handle_start(message)
    else:
        if message.text == BTN_LIGHT:
            users_db[hashed_id]["light"] = True
            bot.send_message(message.chat.id, MSG_YES_LIGHT)
            save_db()
        elif message.text == BTN_BLACKOUT:
            users_db[hashed_id]["light"] = False
            bot.send_message(message.chat.id, MSG_NO_LIGHT)
            save_db()
        elif message.text == BTN_MAP:
            bot.send_chat_action(message.chat.id, "upload_photo")
            create_plot()
            bot.send_chat_action(message.chat.id, "upload_photo")
            bot.send_photo(message.chat.id, open("image.png", "rb"))


if __name__ == "__main__":
    read_db()
    bot.infinity_polling()
