import datetime
import time
import connector
import telegram
from telegram.ext import CommandHandler, MessageHandler, Filters
from config import TOKEN, LIMIT_COUNT, EXCLUSIVE_MODE, RANK_COMMAND_MODE
import schedule
from task import add_task

bot = telegram.Bot(token=TOKEN)


def start(update, context):
    try:
        connector.get_connection().keys()
        print('进入start函数')
        update.message.reply_text(
            '在呢！本大爷很正常,别打扰我了',
        )
    except Exception as e:
        print(e)
        print('进入start函数')
        update.message.reply_text("系统故障，Redis连接失败，请检查！")
        update.message.reply_text("错误信息：" + str(e))


def rank(update, context):
    try:
        r = connector.get_connection()
        chat_type = update.effective_chat.type
        user_id = update.effective_user.id
        chat_id = update.effective_message.chat_id
        try:
            username = update.effective_user.username
        except Exception as e:
            username = update.effective_user.id
        # 限制为群组
        if chat_type != "supergroup":
            update.message.reply_text("此命令只有在群组中有效")
            return
        if RANK_COMMAND_MODE == 1:
            try:
                chat_member = bot.get_chat_member(chat_id, user_id)
                status = chat_member["status"]
                print("此用户在群组中身份为： {}".format(status))
                if status == "creator" or status == "administrator":
                    print("用户权限正确")
                else:
                    update.message.reply_text("此命令仅对管理员开放")
                    return
            except Exception as e:
                print(e)
                print("获取用户身份失败")
        if r.exists("{}_frequency_limit".format(chat_id)):
            r.setrange("{}_frequency_limit".format(chat_id), 0, int(r.get("{}_frequency_limit".format(chat_id))) + 1)
        else:
            struct_time = time.localtime(time.time())
            # 数据过期时间为当前小时的 59 分
            ex_time = datetime.datetime(
                struct_time.tm_year,
                struct_time.tm_mon,
                struct_time.tm_mday,
                struct_time.tm_hour,
                59
            )
            r.set("{}_frequency_limit".format(chat_id), 1)
            r.expireat("{}_frequency_limit".format(chat_id), ex_time)
        count = int(r.get("{}_frequency_limit".format(chat_id)))
        if count > LIMIT_COUNT:
            update.message.reply_text("都点了那么多次了还点,hy附体了")
            return
        add_task(chat_id)
        print("群组: {}，用户: {}|{} 发起了主动触发请求".format(chat_id, username, user_id, ))
        update.message.reply_text("品云的水逼们,准备好击剑了吗,要来了~")
    except Exception as e:
        print("主动触发任务失败，请检查")
        print(e)


def chat_content_exec(update, context):
    try:
        r = connector.get_connection()
        text = update.message.text
        chat_type = update.effective_chat.type
        user_id = update.effective_user.id
        chat_id = update.effective_message.chat_id
        # 限制为群组
        if chat_type != "supergroup":
            return
        # 限制文字长度不能超过80字
        if len(text) > 80:
            return
        # 独享模式（仅授权群组可用）
        if EXCLUSIVE_MODE == 1 and chat_id not in ["1231242141"]:
            print(chat_id + " 为未认证群组，取消入库")
            return
        try:
            username = update.effective_user.username
        except Exception as e:
            username = update.effective_user.id
        user = update.message.from_user
        firstname = str(user["first_name"])
        lastname = str(user["last_name"])
        name = ""
        if firstname != "None":
            name = firstname
        elif lastname != "None":
            name = lastname
        elif len(name) == 0:
            name = username
        print("\n---------------------------")
        print("内容: " + text[:10])
        print("群组类型: " + str(chat_type))
        print("用户ID: " + str(user_id))
        print("chat_id: " + str(chat_id))
        if "/" in text:
            print("这是一条指令信息，跳过")
            return
        else:
            if text[-1] not in ["，", "。", "！", "：", "？", "!", "?", ",", ":", "."]:
                r.append("{}_chat_content".format(chat_id), text + "。")
            else:
                r.append("{}_chat_content".format(chat_id), text)
            r.incrby("{}_total_message_amount".format(chat_id))
            r.hincrby("{}_user_message_amount".format(chat_id), name)
            r.hincrby("{}_userid_message_amount".format(chat_id), user_id)
        print("---------------------------")
    except Exception as e:
        print(e)
        print("用户数据提取、入库错误")


def check_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)


start_handler = CommandHandler('start', start)
rank_handler = CommandHandler('rank', rank)
chat_content_handler = MessageHandler(Filters.text, chat_content_exec)
