from setup import *
import telebot
import csv
import datetime
from pycbrf.toolbox import ExchangeRates

bot = telebot.TeleBot(myConfig['token'])
chats_online = {}
notes_list = []

def isISIN(ms):
    if (ms[:2].lower() in (['xs','ch','ru'])) and (len(ms)==12):
        for c in ms[2:]:
            if not c in ('0123456789'):
                return False
        return True
    else:
        return False

@bot.message_handler(commands=['start', 'help'])
def process_command(message):
#    if not message.from_user.username.lower() in bot_users:
#        bot.send_message(message.chat.id, f'К сожалению, ваше telegram-имя {message.from_user.username} отсутствует в списке зарегистрированных пользователей.\nСвяжитесь с автором сервиса чтобы это исправить.')
#        return
    bot.send_message(message.chat.id, 'Привет! Это система поддержки структурных нот.\n\nВведи isin-код ноты, которая погасилась ДОСРОЧНО, и я посчитаю для тебя её чистую доходность.')

@bot.message_handler(content_types = ['text'])
def process_command(message):
    ms = message.text.strip()
    if isISIN(ms):
        chats_online[message.chat.id] = ms
        for row in notes_list:
            if (row['ISIN'] == ms):
                if (row["CALLED"]=="1"):
                    if float(row["COUPON"].strip("%").replace(",","."))>0:
                        s = f'_Нота "{row["NAME"]}" в {row["CUR"]}\nПлановый срок с {row["START"]} по {row["END"]}\nДосрочное погашение {row["AUTOCALL_DATE"]}_'
                        start_date = datetime.datetime.strptime(row["START"], '%d.%m.%Y')
                        end_date = datetime.datetime.strptime(row["AUTOCALL_DATE"], '%d.%m.%Y')
                        quarters = round((end_date - start_date).days/(365/4))
                        s += f'\n\nНота проработала {quarters} квартала/-ов с купоном {row["COUPON"]}.'
                        coupon = float(row["COUPON"].strip("%").replace(",",".")) * 0.87 / 4 * quarters
                        if row["COMISSION"] == "":
                            digit_comission = 2.0
                            comis_str = 'точных данных нет, условно взята 2%'
                        else:
                            digit_comission = float(row["COMISSION"].strip("%").replace(",","."))
                            comis_str = row["COMISSION"]
                        profit = coupon -  digit_comission
                        s += f'\nДоход по ноте *{round(profit,2)}%* с учетом НДФЛ на купоны и уплаченной комисии при покупке ({comis_str}).'

                        start_rates = ExchangeRates(start_date.strftime('%Y-%m-%d'))
                        end_rates = ExchangeRates(end_date.strftime('%Y-%m-%d'))
                        start_curs = start_rates[row["CUR"]].value
                        end_curs = end_rates[row["CUR"]].value
                        cur_tax = max(float(end_curs - start_curs) * 0.13 / float(end_curs) * 100,0)
                        s += f'\nКурс валюты изменился:\n      с {start_curs} на дату запуска {row["START"]}\n      до {end_curs} на дату погашения {row["AUTOCALL_DATE"]}\n'
                        if end_curs > start_curs:
                            s += f'Налог на переоценку составит *{round(cur_tax,2)}%* от суммы инвестиции.'
                        else:
                            s += 'Налога на переоценку нет.'

                        s += f'\n\n*ОБЩИЙ ДОХОД СОСТАВИЛ {round(profit-cur_tax,2)}%* без учета накладных\n*ЭТО РАВНОЗНАЧНО ДОХОДНОСТИ {round((profit-cur_tax)/quarters*4, 2)}% ГОДОВЫХ*'
                        s += f'\n\nНакладные расходы (Депозитарий, НРД) составили {900/start_curs:.2} {row["CUR"]}\n(разделите их на сумму вложения и вычтите из общего дохода)'

                        bot.send_message(message.chat.id, s, parse_mode= 'Markdown')
                    else:
                        bot.send_message(message.chat.id, f'Не могу понять величину купона по этой ноте. А без этого и доход не посчитать. ((\nИзвините, пожалуйста!')
                else:
                    bot.send_message(message.chat.id, f'Указанная Вами нота еще не погашена (по крайней мере, так указано в моей базе).\nВозможно мой нерасторопный создатель еще не внес соответствующее наблюдение погашения.\nИзвиняюсь за него!')
    else:
        bot.send_message(message.chat.id, f'Извините, введённое значние не выглядит как ISIN-код.\nВсе структурные продукты в моей базе имеют код, который начинается на "XS", "CH" или "RU", и далее следуют 10 цифр.\nПроверьте значение и попробуйте еще раз.')

def RefreshBase():
    watches_list = []
    with open('watches.csv', encoding="cp1251") as csvfile:
        watches_reader = csv.DictReader(csvfile, delimiter=';')
        for row in watches_reader:
            watches_list.append(row)

    with open('notes.csv', encoding="cp1251") as csvfile:
        notes_reader = csv.DictReader(csvfile, delimiter=';')
        for row in notes_reader:
            for watch in watches_list:
                if watch["ISIN"]==row["ISIN"]:
                    row["AUTOCALL_DATE"]=watch["DATE"]
            notes_list.append(row)

RefreshBase()
bot.polling(interval=0)