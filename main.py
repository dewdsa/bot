import os
import sys
import subprocess
import signal
import asyncio
import shutil
import psutil
import tempfile
from pathlib import Path
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = "8544085278:AAHKcE1vAeBtCjnJlStETD_wFWBRVm_fprw"
ALLOWED_USERS = {1914849129}

processes = {}
current_dir = os.getcwd()

def escape_md(text: str) -> str:
    return text.replace("`", "\\`").replace("*", "\\*").replace("_", "\\_")

async def auth_check(update: Update) -> bool:
    if not ALLOWED_USERS:
        return True
    return update.effective_user.id in ALLOWED_USERS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_check(update):
        await update.message.reply_text("❌ Sizga ruxsat yo'q!")
        return
    keyboard = [
        [InlineKeyboardButton("📁 Files", callback_data="files")],
        [InlineKeyboardButton("💻 Terminal", callback_data="terminal")],
        [InlineKeyboardButton("▶️ Processes", callback_data="processes")],
        [InlineKeyboardButton("📊 System Info", callback_data="sysinfo")],
        [InlineKeyboardButton("🔧 Tools", callback_data="tools")],
    ]
    await update.message.reply_text(
        "*Server Management Bot*\n\nKerakli bo'limni tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_check(update):
        await update.message.reply_text("❌ Sizga ruxsat yo'q!")
        return
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("📁 Files", callback_data="files")],
        [InlineKeyboardButton("💻 Terminal", callback_data="terminal")],
        [InlineKeyboardButton("▶️ Processes", callback_data="processes")],
        [InlineKeyboardButton("📊 System Info", callback_data="sysinfo")],
        [InlineKeyboardButton("🔧 Tools", callback_data="tools")],
    ]
    await query.edit_message_text(
        "*Server Management Bot*\n\nKerakli bo'limni tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def files_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("📂 ls - Fayllar ro'yxati", callback_data="ls")],
        [InlineKeyboardButton("⬆️ Upload", callback_data="upload")],
        [InlineKeyboardButton("⬇️ Download", callback_data="download")],
        [InlineKeyboardButton("🗑️ Delete", callback_data="delete")],
        [InlineKeyboardButton("📁 New Folder", callback_data="mkdir")],
        [InlineKeyboardButton("🔙 Back", callback_data="menu")],
    ]
    await query.edit_message_text(
        f"*📁 Fayllar boshqaruvi*\n\nJoriy papka: `{escape_md(current_dir)}`",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def ls_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_dir
    if not await auth_check(update):
        return
    try:
        items = os.listdir(current_dir)
        text = f"*📂 {escape_md(current_dir)}*\n\n"
        for item in sorted(items):
            path = os.path.join(current_dir, item)
            icon = "📁" if os.path.isdir(path) else "📄"
            size = ""
            if os.path.isfile(path):
                try:
                    size = f" ({os.path.getsize(path)} bytes)"
                except:
                    pass
            text += f"{icon} `{escape_md(item)}`{size}\n"
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {escape_md(str(e))}", parse_mode="Markdown")

async def terminal_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("💻 Exec Command", callback_data="exec")],
        [InlineKeyboardButton("▶️ Run Code", callback_data="runcode")],
        [InlineKeyboardButton("⏹️ Stop Process", callback_data="stopprocess")],
        [InlineKeyboardButton("🔙 Back", callback_data="menu")],
    ]
    await query.edit_message_text(
        "*💻 Terminal*\n\nBuyruq yuboring yoki quyidagilardan birini tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def exec_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_check(update):
        return
    if not update.message:
        return
    cmd = update.message.text.strip()
    if cmd.startswith("/exec "):
        cmd = cmd[5:]
    
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=60,
            cwd=current_dir
        )
        output = result.stdout + result.stderr
        if not output:
            output = "(Hech qanday chiqish yo'q)"
        await update.message.reply_text(
            f"```\n{escape_md(output[:4000])}\n```",
            parse_mode="Markdown"
        )
    except subprocess.TimeoutExpired:
        await update.message.reply_text("⏱️ Vaqt tugadi!")
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {escape_md(str(e))}", parse_mode="Markdown")

async def runcode_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🐍 Python", callback_data="run_python")],
        [InlineKeyboardButton("📜 Bash", callback_data="run_bash")],
        [InlineKeyboardButton("📦 Node.js", callback_data="run_node")],
        [InlineKeyboardButton("🔙 Back", callback_data="terminal")],
    ]
    await query.edit_message_text(
        "*▶️ Kod ishga tushirish*\n\nTilni tanlang yoki kod yuboring:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def processes_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "*▶️ Faol processlar*\n\n"
    for pid, info in processes.items():
        text += f"• `{pid}` - {escape_md(info['name'][:30])}\n"
    
    if not processes:
        text += "Processlar yo'q"
    
    keyboard = [
        [InlineKeyboardButton("🔙 Back", callback_data="menu")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

def get_sysinfo():
    try:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        return cpu, mem.percent, mem.used//1024//1024, mem.total//1024//1024, disk.percent, disk.used//1024//1024//1024, disk.total//1024//1024//1024
    except:
        return 0, 0, 0, 0, 0, 0, 0

async def sysinfo_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    cpu, mem_perc, mem_used, mem_total, disk_perc, disk_used, disk_total = get_sysinfo()
    
    text = f"""*📊 Tizim ma'lumotlari*

🔹 CPU: {cpu}%
🔹 RAM: {mem_perc}% ({mem_used}MB / {mem_total}MB)
🔹 Disk: {disk_perc}% ({disk_used}GB / {disk_total}GB)
🔹 Processlar: {len(psutil.pids())}"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh", callback_data="sysinfo")],
        [InlineKeyboardButton("🔙 Back", callback_data="menu")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def tools_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("📦 Install Package", callback_data="install")],
        [InlineKeyboardButton("📋 Pip List", callback_data="pip_list")],
        [InlineKeyboardButton("🌐 Curl", callback_data="curl")],
        [InlineKeyboardButton("🔙 Back", callback_data="menu")],
    ]
    await query.edit_message_text(
        "*🔧 Tools*\n\nQuyidagilardan birini tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_check(update):
        return
    doc = update.message.document
    if not doc:
        return
    try:
        file = await doc.get_file()
        path = os.path.join(current_dir, doc.file_name)
        await file.download_to_drive(path)
        await update.message.reply_text(f"✅ Saqlandi: `{escape_md(path)}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {escape_md(str(e))}", parse_mode="Markdown")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_check(update):
        return
    photo = update.message.photo[-1] if update.message.photo else None
    if not photo:
        return
    try:
        file = await photo.get_file()
        path = os.path.join(current_dir, f"photo_{photo.file_id}.jpg")
        await file.download_to_drive(path)
        await update.message.reply_text(f"✅ Saqlandi: `{escape_md(path)}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {escape_md(str(e))}", parse_mode="Markdown")

async def cd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_dir
    if not await auth_check(update):
        return
    if not update.message:
        return
    args = update.message.text.strip().split()
    if len(args) < 2:
        await update.message.reply_text(f"📂 Joriy papka: `{escape_md(current_dir)}`", parse_mode="Markdown")
        return
    
    new_dir = args[1]
    if new_dir.startswith("/"):
        target = new_dir
    else:
        target = os.path.join(current_dir, new_dir)
    
    if os.path.isdir(target):
        current_dir = os.path.abspath(target)
        await update.message.reply_text(f"✅ Papka o'zgardi: `{escape_md(current_dir)}`", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Papka topilmadi!", parse_mode="Markdown")

async def download_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_check(update):
        return
    if not update.message:
        return
    
    args = update.message.text.strip().split(maxsplit=1)
    if len(args) < 2:
        await update.message.reply_text("Usage: /download <fayl_nomi>", parse_mode="Markdown")
        return
    
    filename = args[1]
    filepath = os.path.join(current_dir, filename)
    
    if not os.path.exists(filepath):
        await update.message.reply_text("❌ Fayl topilmadi!", parse_mode="Markdown")
        return
    
    try:
        if os.path.isfile(filepath):
            await update.message.reply_document(document=open(filepath, 'rb'))
        elif os.path.isdir(filepath):
            shutil.make_archive(filepath, 'zip', filepath)
            await update.message.reply_document(document=open(filepath + '.zip', 'rb'))
            os.remove(filepath + '.zip')
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {escape_md(str(e))}", parse_mode="Markdown")

async def delete_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_check(update):
        return
    if not update.message:
        return
    
    args = update.message.text.strip().split(maxsplit=1)
    if len(args) < 2:
        await update.message.reply_text("Usage: /delete <fayl_nomi>", parse_mode="Markdown")
        return
    
    filename = args[1]
    filepath = os.path.join(current_dir, filename)
    
    if not os.path.exists(filepath):
        await update.message.reply_text("❌ Fayl topilmadi!", parse_mode="Markdown")
        return
    
    try:
        if os.path.isfile(filepath):
            os.remove(filepath)
        elif os.path.isdir(filepath):
            shutil.rmtree(filepath)
        await update.message.reply_text(f"✅ O'chirildi: `{escape_md(filepath)}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {escape_md(str(e))}", parse_mode="Markdown")

async def mkdir_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_dir
    if not await auth_check(update):
        return
    if not update.message:
        return
    
    args = update.message.text.strip().split(maxsplit=1)
    if len(args) < 2:
        await update.message.reply_text("Usage: /mkdir <papka_nomi>", parse_mode="Markdown")
        return
    
    dirname = args[1]
    dirpath = os.path.join(current_dir, dirname)
    
    try:
        os.makedirs(dirpath, exist_ok=True)
        await update.message.reply_text(f"✅ Yaratildi: `{escape_md(dirpath)}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {escape_md(str(e))}", parse_mode="Markdown")

async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global processes
    if not await auth_check(update):
        return
    if not update.message:
        return
    
    args = update.message.text.strip().split(maxsplit=1)
    if len(args) < 2:
        await update.message.reply_text("Usage: /run <buyruq>", parse_mode="Markdown")
        return
    
    cmd = args[1]
    
    try:
        proc = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=current_dir
        )
        processes[proc.pid] = {"name": cmd, "proc": proc}
        
        async def monitor():
            await asyncio.sleep(2)
            try:
                stdout, stderr = proc.communicate(timeout=30)
                output = stdout.decode() + stderr.decode()
                if update.message:
                    await update.message.reply_text(
                        f"```\n{escape_md(output[:4000])}\n```",
                        parse_mode="Markdown"
                    )
            except subprocess.TimeoutExpired:
                pass
            finally:
                if proc.pid in processes:
                    del processes[proc.pid]
        
        asyncio.create_task(monitor())
        await update.message.reply_text(f"✅ Ishga tushdi! PID: `{proc.pid}`", parse_mode="Markdown")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {escape_md(str(e))}", parse_mode="Markdown")

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global processes
    if not await auth_check(update):
        return
    if not update.message:
        return
    
    args = update.message.text.strip().split(maxsplit=1)
    if len(args) < 2:
        await update.message.reply_text("Usage: /stop <PID>", parse_mode="Markdown")
        return
    
    try:
        pid = int(args[1])
        if pid in processes:
            proc = processes[pid]["proc"]
            proc.terminate()
            del processes[pid]
            await update.message.reply_text(f"✅ To'xtatildi! PID: `{pid}`", parse_mode="Markdown")
        else:
            try:
                os.kill(pid, signal.SIGTERM)
                await update.message.reply_text(f"✅ To'xtatildi! PID: `{pid}`", parse_mode="Markdown")
            except:
                await update.message.reply_text("❌ Process topilmadi!", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {escape_md(str(e))}", parse_mode="Markdown")

async def install_package(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_check(update):
        return
    if not update.message:
        return
    
    args = update.message.text.strip().split(maxsplit=1)
    if len(args) < 2:
        await update.message.reply_text("Usage: /install <package_name>", parse_mode="Markdown")
        return
    
    package = args[1]
    
    try:
        result = subprocess.run(
            ["pip", "install", package, "-q"],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            await update.message.reply_text(f"✅ O'rnatildi: `{escape_md(package)}`", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ Xato: {escape_md(result.stderr[:1000])}", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {escape_md(str(e))}", parse_mode="Markdown")

async def pip_list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_check(update):
        return
    if not update.message:
        return
    
    try:
        result = subprocess.run(
            ["pip", "list"],
            capture_output=True, text=True
        )
        await update.message.reply_text(
            f"```\n{escape_md(result.stdout[:4000])}\n```",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {escape_md(str(e))}", parse_mode="Markdown")

async def curl_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_check(update):
        return
    if not update.message:
        return
    
    args = update.message.text.strip().split(maxsplit=1)
    if len(args) < 2:
        await update.message.reply_text("Usage: /curl <url>", parse_mode="Markdown")
        return
    
    url = args[1]
    
    try:
        result = subprocess.run(
            ["curl", "-s", url],
            capture_output=True, text=True, timeout=30
        )
        await update.message.reply_text(
            f"```\n{escape_md(result.stdout[:4000])}\n```",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {escape_md(str(e))}", parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_check(update):
        return
    text = """*📋 Buyruqlar ro'yxati*

/start - Botni ishga tushirish
/cd <papka> - Papka o'zgartirish
/ls - Fayllar ro'yxati
/mkdir <nomi> - Papka yaratish
/delete <fayl> - Fayl o'chirish
/download <fayl> - Fayl yuklab olish

/exec <buyruq> - Buyruq ishga tushirish
/run <buyruq> - Process ishga tushirish
/stop <PID> - Process to'xtatish

/install <paket> - Python paket o'rnatish
/pip list - Paketlar ro'pyxati
/curl <url> - URL so'rov

/sysinfo - Tizim ma'lumotlari
/help - Yordam"""
    await update.message.reply_text(text, parse_mode="Markdown")

async def sysinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_check(update):
        return
    cpu, mem_perc, mem_used, mem_total, disk_perc, disk_used, disk_total = get_sysinfo()
    
    text = f"""*📊 Tizim ma'lumotlari*

🔹 CPU: {cpu}%
🔹 RAM: {mem_perc}% ({mem_used}MB / {mem_total}MB)
🔹 Disk: {disk_perc}% ({disk_used}GB / {disk_total}GB)
🔹 Processlar: {len(psutil.pids())}"""
    await update.message.reply_text(text, parse_mode="Markdown")

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ls", ls_command))
    app.add_handler(CommandHandler("cd", cd_command))
    app.add_handler(CommandHandler("mkdir", mkdir_command))
    app.add_handler(CommandHandler("delete", delete_file))
    app.add_handler(CommandHandler("download", download_file))
    app.add_handler(CommandHandler("exec", exec_command))
    app.add_handler(CommandHandler("run", run_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("install", install_package))
    app.add_handler(CommandHandler("pip", pip_list_cmd))
    app.add_handler(CommandHandler("curl", curl_command))
    app.add_handler(CommandHandler("sysinfo", sysinfo_command))
    
    app.add_handler(CallbackQueryHandler(menu, pattern="menu"))
    app.add_handler(CallbackQueryHandler(files_menu, pattern="files"))
    app.add_handler(CallbackQueryHandler(terminal_menu, pattern="terminal"))
    app.add_handler(CallbackQueryHandler(processes_menu, pattern="processes"))
    app.add_handler(CallbackQueryHandler(sysinfo_menu, pattern="sysinfo"))
    app.add_handler(CallbackQueryHandler(tools_menu, pattern="tools"))
    app.add_handler(CallbackQueryHandler(runcode_menu, pattern="runcode"))
    
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, exec_command))
    
    print("🤖 Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
