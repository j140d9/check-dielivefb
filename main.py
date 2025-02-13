import json
import asyncio
import aiohttp  # Thay thế requests bằng aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from keep_alive import keep_alive

TOKEN = "7993371378:AAHv0jEzvhtMcTHEEtejR2VmH_bhBgE7xRA"
ADMIN_FILE = "admin.json"
UID_FILE = "uid_list.json"

# Initialize Bot
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# Initialize Dispatcher with bot property
dp = Dispatcher()


# Load admin IDs
def load_admins():
    try:
        with open(ADMIN_FILE, "r") as f:
            return json.load(f).get("admins", [])
    except FileNotFoundError:
        return []


def save_admins(admins):
    with open(ADMIN_FILE, "w") as f:
        json.dump({"admins": admins}, f)


# Load UID list
def load_uids():
    try:
        with open(UID_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_uids(uids):
    with open(UID_FILE, "w") as f:
        json.dump(uids, f)


# Check if user is admin
def is_admin(user_id):
    admins = load_admins()
    # Kiểm tra xem user_id có trong danh sách admins không
    return any(admin['id'] == user_id for admin in admins)


# Command to add UID
async def add_uid(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.reply(
            f"Bạn không có quyền sử dụng lệnh này. ID: {message.from_user.id}")
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.reply("Cách dùng: /add <uid> <ghi chú>")
        return

    uid, note = args[1], args[2]

    # Check if UID is valid (for example, make sure it's numeric)
    if not uid.isdigit():
        await message.reply("UID phải là một chuỗi số hợp lệ.")
        return

    uids = load_uids()
    if uid in uids:
        await message.reply("UID đã tồn tại trong danh sách.")
    else:
        uids[uid] = note
        save_uids(uids)
        await message.reply(
            f"Đã thêm UID {uid} vào danh sách với ghi chú: {note}")


# Register the /add command handler using filters
dp.message.register(add_uid, Command("add"))


# Function to check UID status
async def check_uid_status(uid):
    global total_die, total_live
    url = f"https://graph.facebook.com/{uid}/picture?type=normal&redirect=0"

    # Use aiohttp for async HTTP request
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                return "die"

            response_data = await response.json()  # Giả sử response là JSON

            # Kiểm tra điều kiện "die" khi có lỗi với mã lỗi (#100)
            if 'error' in response_data:
                if response_data['error']['code'] == 100 and response_data[
                        'error']['error_subcode'] == 2018218:
                    return "die"
                else:
                    return "die"
            else:
                # Kiểm tra ảnh đại diện và in kết quả live
                image_url = response_data['data'].get('url', '')
                if 'rsrc.php' in image_url:
                    return "die"
                else:
                    return "live"


# Periodic UID checking
async def check_uids():
    while True:
        uids = load_uids()
        if not uids:
            await asyncio.sleep(10)
            continue

        to_remove = []
        for uid in list(uids.keys()):
            status = await check_uid_status(uid)  # Gọi hàm bất đồng bộ
            print(status)
            if status == "live":
                # Gửi thông báo cho tất cả admin
                for admin in load_admins():
                    await bot.send_message(
                        chat_id=admin['id'],
                        text=
                        f"- UID: {uid}\n- Ghi chú: {uids[uid]}\n- Trạng thái: Live\n\n\n- Bot by @mr_necom"
                    )
                to_remove.append(uid)

        # Xóa UID đã được xử lý
        for uid in to_remove:
            del uids[uid]
            save_uids(uids)

        await asyncio.sleep(1)  # Kiểm tra mỗi 1 giây


async def main():
    # Start polling for incoming messages
    asyncio.create_task(check_uids())  # Run UID checking task in parallel
    await dp.start_polling(bot)


if __name__ == "__main__":
    # Start all async tasks
    keep_alive()
    asyncio.run(main())  # Run everything with asyncio.run()
