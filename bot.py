from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, JobQueue
import requests
import re
import os

# 🔐 Cấu hình bot
TOKEN = os.getenv('TELEGRAM_TOKEN', '7785173200:AAH8QFwn0SdYS_jVENStknA4gE2Dbc9ZIgo')  # Lấy từ biến môi trường
NOTIFY_CHAT_ID = int(os.getenv('NOTIFY_CHAT_ID', 1278915994))  # ID chat để thông báo

# 💾 Danh sách lưu UID trong bộ nhớ
saved_uids = {}

# ⚙️ Hàm kiểm tra UID Facebook
def check_facebook_uid(uid):
    url = f'https://www.facebook.com/{uid}'
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if "page not available" in response.text.lower() or response.status_code == 404:
            return False
        return True
    except Exception:
        return False

# 🔗 Hàm trích xuất UID từ link
def extract_uid_from_url(url):
    match = re.search(r'profile\.php\?id=(\d+)', url)
    if match:
        return match.group(1)
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        uid_match = re.search(r'"userID":"(\d+)"', response.text)
        if uid_match:
            return uid_match.group(1)
    except Exception:
        return None
    return None

# 📢 Hàm gửi thông báo
async def send_notify(context: ContextTypes.DEFAULT_TYPE, text: str):
    await context.bot.send_message(chat_id=NOTIFY_CHAT_ID, text=text)

# 🔄 Hàm kiểm tra tự động
async def check_status_changes(context: ContextTypes.DEFAULT_TYPE):
    if not saved_uids:
        return
    changes = []
    for uid in saved_uids.keys():
        current_status = "LIVE" if check_facebook_uid(uid) else "DIE"
        old_status, note = saved_uids[uid]
        if current_status != old_status:
            saved_uids[uid] = [current_status, note]
            changes.append(f"UID {uid}: {old_status} → {current_status} (Ghi chú: {note})")
    if changes:
        msg = "⚠️ **Cập nhật trạng thái UID:**\n" + "\n".join(changes)
        await send_notify(context, msg)

# 🧾 Lệnh /check
async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Vui lòng nhập UID.\nVí dụ: /check 1000123456789")
        return
    uid = context.args[0]
    result = check_facebook_uid(uid)
    msg = f"✅ UID {uid} đang **LIVE**." if result else f"❌ UID {uid} là **DIE** hoặc không tồn tại."
    await update.message.reply_text(msg)

# 🔍 Lệnh /checkuid
async def check_uid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Vui lòng nhập UID.\nVí dụ: /checkuid 1000123456789")
        return
    uid = context.args[0]
    result = check_facebook_uid(uid)
    status = "LIVE" if result else "DIE"
    if uid in saved_uids:
        old_status, note = saved_uids[uid]
        if old_status != status:
            saved_uids[uid] = [status, note]
            msg = f"✅ UID {uid} hiện tại là **{status}** (đã cập nhật từ {old_status}).\nGhi chú: {note}"
        else:
            msg = f"✅ UID {uid} hiện tại là **{status}** (không thay đổi).\nGhi chú: {note}"
    else:
        msg = f"✅ UID {uid} hiện tại là **{status}** (chưa được lưu)."
    await update.message.reply_text(msg)

# 🌐 Lệnh /checklink
async def check_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Vui lòng nhập link.\nVí dụ: /checklink https://www.facebook.com/username")
        return
    url = context.args[0]
    uid = extract_uid_from_url(url)
    if not uid:
        await update.message.reply_text("❌ Không thể trích xuất UID từ link.")
        return
    result = check_facebook_uid(uid)
    status = "LIVE" if result else "DIE"
    if uid in saved_uids:
        old_status, note = saved_uids[uid]
        if old_status != status:
            saved_uids[uid] = [status, note]
            msg = f"✅ UID {uid} từ link hiện tại là **{status}** (đã cập nhật từ {old_status}).\nGhi chú: {note}"
        else:
            msg = f"✅ UID {uid} từ link hiện tại là **{status}** (không thay đổi).\nGhi chú: {note}"
    else:
        msg = f"✅ UID {uid} từ link hiện tại là **{status}** (chưa được lưu)."
    await update.message.reply_text(msg)

# 💾 Lệnh /save
async def save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Vui lòng nhập UID và ghi chú.\nVí dụ: /save 1000123456789 Ghi_chu")
        return
    uid = context.args[0]
    note = " ".join(context.args[1:]) if len(context.args) > 1 else "Không có ghi chú"
    result = check_facebook_uid(uid)
    status = "LIVE" if result else "DIE"
    if uid in saved_uids:
        old_status, old_note = saved_uids[uid]
        msg = f"ℹ️ UID {uid} đã được lưu trước đó với trạng thái {old_status} và ghi chú: {old_note}."
    else:
        saved_uids[uid] = [status, note]
        msg = f"✅ Đã lưu UID {uid} ({status}) với ghi chú: {note}"
    await update.message.reply_text(msg)
    full_notify = (
        f"[THÔNG BÁO] 👤 @{update.effective_user.username or update.effective_user.first_name} "
        f"(ID: {update.effective_user.id}) đã lưu UID:\n➡️ {uid}\n📋 Trạng thái: {status}\n📝 Ghi chú: {note}"
    )
    await send_notify(context, full_notify)

# 📋 Lệnh /list
async def list_saved(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not saved_uids:
        await update.message.reply_text("⚠️ Chưa có UID nào được lưu.")
        return
    msg = "📋 Danh sách UID đã lưu:\n"
    for uid, (status, note) in saved_uids.items():
        msg += f"- {uid}: {status} (Ghi chú: {note})\n"
    await update.message.reply_text(msg)

# ❓ Lệnh /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 **Hướng dẫn sử dụng bot:**\n\n"
        "1. **Kiểm tra UID (cơ bản):**\n   - Lệnh: `/check <UID>`\n   - Ví dụ: `/check 1000123456789`\n"
        "2. **Kiểm tra UID (nâng cao):**\n   - Lệnh: `/checkuid <UID>`\n   - Ví dụ: `/checkuid 1000123456789`\n"
        "3. **Kiểm tra từ link:**\n   - Lệnh: `/checklink <URL>`\n   - Ví dụ: `/checklink https://www.facebook.com/username`\n"
        "4. **Lưu UID:**\n   - Lệnh: `/save <UID> <Ghi chú>`\n   - Ví dụ: `/save 1000123456789 Ghi_chu`\n"
        "5. **Xem danh sách UID:**\n   - Lệnh: `/list`\n"
        "6. **Xem UID DIE:**\n   - Lệnh: `/checkdie`\n"
        "7. **Xem UID LIVE:**\n   - Lệnh: `/checklive`\n"
        "8. **Xem hướng dẫn:**\n   - Lệnh: `/help`\n"
        "💡 **Lưu ý:** Bot tự động kiểm tra trạng thái UID mỗi 5 phút."
    )
    await update.message.reply_text(help_text)

# ❌ Lệnh /checkdie
async def check_die(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not saved_uids:
        await update.message.reply_text("⚠️ Chưa có UID nào được lưu.")
        return
    updated = False
    for uid in saved_uids.keys():
        current_status = "LIVE" if check_facebook_uid(uid) else "DIE"
        old_status, note = saved_uids[uid]
        if current_status != old_status:
            saved_uids[uid] = [current_status, note]
            updated = True
    die_uids = {uid: (status, note) for uid, (status, note) in saved_uids.items() if status == "DIE"}
    if not die_uids:
        await update.message.reply_text("✅ Không có UID nào DIE.")
        return
    msg = "❌ Danh sách UID DIE:\n" + "\n".join(f"- {uid}: {status} (Ghi chú: {note})" for uid, (status, note) in die_uids.items())
    if updated:
        msg += "\nℹ️ Một số trạng thái đã được cập nhật."
    await update.message.reply_text(msg)

# ✅ Lệnh /checklive
async def check_live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not saved_uids:
        await update.message.reply_text("⚠️ Chưa có UID nào được lưu.")
        return
    updated = False
    for uid in saved_uids.keys():
        current_status = "LIVE" if check_facebook_uid(uid) else "DIE"
        old_status, note = saved_uids[uid]
        if current_status != old_status:
            saved_uids[uid] = [current_status, note]
            updated = True
    live_uids = {uid: (status, note) for uid, (status, note) in saved_uids.items() if status == "LIVE"}
    if not live_uids:
        await update.message.reply_text("❌ Không có UID nào LIVE.")
        return
    msg = "✅ Danh sách UID LIVE:\n" + "\n".join(f"- {uid}: {status} (Ghi chú: {note})" for uid, (status, note) in live_uids.items())
    if updated:
        msg += "\nℹ️ Một số trạng thái đã được cập nhật."
    await update.message.reply_text(msg)

# ▶️ Chạy bot
if __name__ == '__main__':
    bot_app = ApplicationBuilder().token(TOKEN).build()

    # Thêm các handler
    bot_app.add_handler(CommandHandler("check", check))
    bot_app.add_handler(CommandHandler("checkuid", check_uid))
    bot_app.add_handler(CommandHandler("checklink", check_link))
    bot_app.add_handler(CommandHandler("save", save))
    bot_app.add_handler(CommandHandler("list", list_saved))
    bot_app.add_handler(CommandHandler("help", help_command))
    bot_app.add_handler(CommandHandler("checkdie", check_die))
    bot_app.add_handler(CommandHandler("checklive", check_live))

    # Thiết lập JobQueue
    job_queue = bot_app.job_queue
    job_queue.run_repeating(check_status_changes, interval=300, first=10)

    print("🤖 Bot Telegram đang chạy trên Render...")
    bot_app.run_polling(allowed_updates=Update.ALL_TYPES)