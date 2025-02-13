import json
import asyncio
import aiohttp  # Thay thế requests bằng aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from urllib.parse import urlencode
TOKEN = "7993371378:AAHv0jEzvhtMcTHEEtejR2VmH_bhBgE7xRA"
ADMIN_FILE = "admin.json"
UID_FILE = "uid_list.json"
CASSO_API_KEY = "AK_CS.565254d0e38011efa35d3bccdd557a34.Nkdak9XlSufUnbvXuvhvdRETiMXNuScjyAHoRbElVDxChZGxPvyB8PetG2zCjiuL4ZWNdVim"

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
    return any(admin['id'] == user_id for admin in admins)

# Function to create payment QR code
async def create_payment_qr(user_id):
    amount = 10000
    description = f"TTCFBDL {user_id}"
    bank_account = "100877127751"
    bank_name = "VietinBank"
    
    # Create a dictionary for the query parameters
    params = {
        'acc': bank_account,
        'bank': bank_name,
        'amount': amount,
        'des': description,
        'template': 'compact',
        'download': 'no'
    }
    
    # Encode the parameters and construct the QR URL
    urlencodes = urlencode(params)
    qr_url = f"https://qr.sepay.vn/img?{urlencodes}"
    
    return qr_url

# Function to check payment status
async def check_payment_status(user_id):
    url = "https://oauth.casso.vn/v2/transactions"
    headers = {"Authorization": f"Apikey {CASSO_API_KEY}"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                transactions = await response.json()
                for transaction in transactions.get("data", []):
                    if f"TTCFBDL {user_id}" in transaction.get("description", ""):
                        return True
    return False

# Command to request admin access
async def request_admin(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    if is_admin(user_id):
        await message.reply("Bạn đã là admin.")
        return
    
    qr_url = await create_payment_qr(user_id)
    await message.reply(f"Vui lòng thanh toán để trở thành admin: {qr_url}")
    
    await asyncio.sleep(60)  # Đợi 60 giây để kiểm tra giao dịch
    if await check_payment_status(user_id):
        new_admins = load_admins()
        new_admins.append({"id": user_id, "username": username})
        save_admins(new_admins)
        await message.reply("Thanh toán thành công! Bạn đã trở thành admin.")
    else:
        await message.reply("Chưa nhận được thanh toán. Vui lòng thử lại sau.")

dp.message.register(request_admin, Command("request_admin"))

# Command to add UID
async def add_uid(message: types.Message):
    if not is_admin(message.from_user.id):
        await request_admin(message)
        await message.reply(f"Bạn không có quyền sử dụng lệnh này. ID: {message.from_user.id}")
        return
    
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.reply("Cách dùng: /add <uid> <ghi chú>")
        return
    
    uid, note = args[1], args[2]
    if not uid.isdigit():
        await message.reply("UID phải là một chuỗi số hợp lệ.")
        return

    uids = load_uids()
    if uid in uids:
        await message.reply("UID đã tồn tại trong danh sách.")
    else:
        uids[uid] = {"note": note, "owner": message.from_user.id}
        save_uids(uids)
        await message.reply(f"Đã thêm UID {uid} vào danh sách với ghi chú: {note}")

dp.message.register(add_uid, Command("add"))

# Function to check UID status
async def check_uid_status(uid):
    url = f"https://graph.facebook.com/{uid}/picture?type=normal&redirect=0"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                return "die"
            response_data = await response.json()
            if 'error' in response_data:
                return "die"
            image_url = response_data['data'].get('url', '')
            return "live" if 'rsrc.php' not in image_url else "die"

# Periodic UID checking
async def check_uids():
    while True:
        uids = load_uids()
        if not uids:
            await asyncio.sleep(10)
            continue
        
        for uid, info in list(uids.items()):
            status = await check_uid_status(uid)
            if status == "live":
                owner_id = info["owner"]
                await bot.send_message(chat_id=owner_id, text=f"- UID: {uid}\n- Ghi chú: {info['note']}\n- Trạng thái: Live")
                del uids[uid]
                save_uids(uids)
        
        await asyncio.sleep(1)

async def main():
    asyncio.create_task(check_uids())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
