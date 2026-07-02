import asyncio
import logging
import os
import io
import requests
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, BufferedInputFile, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.chat_action import ChatActionSender
from aiogram.client.default import DefaultBotProperties
from deep_translator import GoogleTranslator  # Konfliktsiz, mutlaqo yangi xavfsiz tarjimon
from groq import Groq

# --- KONFIGURATSIYA ---
TOKEN = "8753014084:AAGynRusQzDXk53ZQMv2SBzBHG8LZM72LIs"
GROQ_API_KEY = "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"

AUTHOR = "Gulmuratov Javohir"
SCHOOL = "Dehqonobod tumani Ixtisoslashgan maktabi"
CLASS = "6-A sinf"
ADMIN_ID = 5492502957
DB_FILE = "users.txt"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
groq_client = Groq(api_key=GROQ_API_KEY)
translator = GoogleTranslator(source='uz', target='en')  # Yangi sozlama

logging.basicConfig(level=logging.INFO)

class AdminStates(StatesGroup):
    waiting_for_ad_text = State()

# --- BAZA ---
def add_user(user_id):
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f: f.write("")
    with open(DB_FILE, "r") as f:
        users = f.read().splitlines()
    if str(user_id) not in users:
        with open(DB_FILE, "a") as f:
            f.write(f"{user_id}\n")

def get_users():
    if not os.path.exists(DB_FILE): return []
    with open(DB_FILE, "r") as f:
        return f.read().splitlines()

# --- MENYULAR ---
def get_main_menu(user_id):
    buttons = [
        [KeyboardButton(text="🎨 Rasm chizish"), KeyboardButton(text="💬 Suhbatlashish")],
        [KeyboardButton(text="👨‍💻 Muallif"), KeyboardButton(text="⚡ Holat")]
    ]
    if user_id == ADMIN_ID:
        buttons.append([KeyboardButton(text="🔐 Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_admin_menu():
    buttons = [
        [KeyboardButton(text="📢 Xabar yuborish")],
        [KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="🔙 Orqaga")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- START ---
@dp.message(Command("start"))
async def start_command(message: Message):
    add_user(message.from_user.id)
    text = (
        f"Assalomu alaykum, <b>{message.from_user.first_name}!</b> 👋\n\n"
        f"Men sun'iy intellekt yordamida ishlovchi <b>Javohir AI</b> botiman. ✨\n"
        f"Quyidagi menyu orqali imkoniyatlarimdan foydalanishingiz mumkin:\n\n"
        f"🎨 <b>Rasm yaratish</b> — Nima rasm kerakligini yozsangiz, chizib beraman.\n"
        f"💬 <b>Suhbatlashish</b> — Istalgan savolingizga aqlli javob beraman.\n"
        f"📊 <b>Holat</b> — Botning tezligi va limitlari haqida ma'lumot.\n"
        f"👨‍💻 <b>Muallif</b> — Bot yaratuvchisi haqida ma'lumot.\n\n"
        f"💡 <b>Eslatma:</b> Rasm chizdirish uchun so'rovingiz oxiriga <b>'rasmi'</b> so'zini qo'shishni unutmang! 👇"
    )
    await message.answer(text, reply_markup=get_main_menu(message.from_user.id))

# --- TUGMALAR ---
@dp.message(F.text == "🎨 Rasm chizish")
async def rasm_btn(message: Message):
    # SEN AYTGAN MATN NUQTA-VERGULIGACHA JOYIDA TURIBDI!
    await message.answer("🎨 <b>Nima rasm chizib beray?</b>\n\nMarhamat, rasm nomini yozing (oxiriga <b>'rasmi'</b> so'zini qo'shing). ✨")

@dp.message(F.text == "💬 Suhbatlashish")
async def chat_btn_info(message: Message):
    await message.answer("💬 Savolingizni yo'llang: 👇")

@dp.message(F.text == "👨‍💻 Muallif")
async def author_info(message: Message):
    text = (
        f"💎 <b>Bot Yaratuvchisi:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👦 <b>Ism:</b> {AUTHOR} 😎\n"
        f"🏫 <b>Maktab:</b> {SCHOOL} 🎓\n"
        f"📚 <b>Sinf:</b> {CLASS} ✨\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🚀 <i>Kelajak dasturchisi tomonidan tayyorlandi!</i>"
    )
    await message.answer(text)

@dp.message(F.text == "🔐 Admin Panel")
async def admin_panel(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("👑 <b>Boshqaruv paneli:</b>", reply_markup=get_admin_menu())

@dp.message(F.text == "📊 Statistika")
async def admin_stat(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(f"👥 Jami a'zolar: {len(get_users())} ta")

@dp.message(F.text == "📢 Xabar yuborish")
async def ad_start(message: Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("📝 <b>Xabar matnini yozing:</b>", reply_markup=ReplyKeyboardRemove())
        await state.set_state(AdminStates.waiting_for_ad_text)

@dp.message(AdminStates.waiting_for_ad_text)
async def ad_send(message: Message, state: FSMContext):
    users = get_users()
    count = 0
    await message.answer("📤 Yuborilmoqda...")
    for user_id in users:
        try:
            await bot.send_message(chat_id=user_id, text=message.text)
            count += 1
            await asyncio.sleep(0.05)
        except: continue
    await state.clear()
    await message.answer(f"✅ {count} ta odamga yetkazildi!", reply_markup=get_main_menu(message.from_user.id))

@dp.message(F.text == "🔙 Orqaga")
async def back_to_main(message: Message):
    await message.answer("Asosiy menyu 👇", reply_markup=get_main_menu(message.from_user.id))

@dp.message(F.text == "⚡ Holat")
async def status_info(message: Message):
    await message.answer("🚀 <b>AI Tizimi:</b> Groq Llama 3 & Microsoft Bing ✨\n🟢 <b>Holat:</b> Online (100% Barqaror) ✅\n🛡 <b>Server:</b> Chaqmoqdek tez va xavfsiz")

# --- AI LOGIKASI ---
@dp.message()
async def handle_logic(message: Message):
    if not message.text: return
    user_text = message.text
    image_keys = ["rasm", "rasmi", "chiz", "surat"]
    
    # --- 🎨 MICROSOFT BING IMAGE CREATOR (DALL-E 3) ---
    if any(word in user_text.lower() for word in image_keys):
        async with ChatActionSender.upload_photo(chat_id=message.chat.id, bot=bot):
            try:
                prompt_uz = user_text.lower()
                for w in image_keys: prompt_uz = prompt_uz.replace(w, "")
                prompt_clean = prompt_uz.strip()
                
                if not prompt_clean:
                    await message.answer("🎨 Rasm chizish uchun biron narsa yozing. Masalan: <i>'Mashina rasmi'</i>")
                    return
                
                # Yangi xavfsiz tarjimon orqali inglizchaga o'girish
                prompt_en = await asyncio.get_event_loop().run_in_executor(None, lambda: translator.translate(prompt_clean))
                
                final_prompt = f"Professional photography of {prompt_en}, ultra detailed, 8k, photorealistic, microsoft bing image creator style"
                image_url = f"https://image.pollinations.ai/prompt/{final_prompt.replace(' ', '%20')}?width=1024&height=1024&nologo=true&model=dalle-3"
                
                res = await asyncio.get_event_loop().run_in_executor(None, lambda: requests.get(image_url, timeout=90))
                
                if res.status_code == 200:
                    image_bytes = io.BytesIO(res.content).getvalue()
                    input_file = BufferedInputFile(image_bytes, filename="bing_dalle.jpg")
                    await message.answer_photo(input_file, caption=f"🎨 <b>Muallif: {AUTHOR}</b>")
                else:
                    await message.answer("❌ Hozirda rasm serveri band. Keyinroq urinib ko'ring.")
            except Exception as e:
                logging.error(f"Rasm xatosi: {e}")
                await message.answer("❌ Rasm yaratishda xatolik bo'ldi. Iltimos, qaytadan urinib ko'ring.")
                
    # --- 💬 MATNLIK SUHBAT (GROQ) ---
    else:
        async with ChatActionSender.typing(chat_id=message.chat.id, bot=bot):
            try:
                sys_msg = f"Sening isming Javohir AI. Seni {AUTHOR} ismli bola yaratgan. U {SCHOOL} maktabining {CLASS}ida o'qiydi. Google, OpenAI yoki Groq haqida gapirma. Agar kim seni yaratganini so'rasa  ayt boshqa payti seni Kim yaratgani haqida gapirma. Faqat o'zbekcha javob ber va har bir javobda mos chiroyli emojilardan/stikerlardan ko'p foydalan."
                
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: groq_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": sys_msg},
                            {"role": "user", "content": user_text}
                        ],
                        temperature=0.7
                    )
                )
                
                final_text = response.choices[0].message.content.replace("**", "").replace("*", "")
                
                bot_keywords = ["kimsan", "yaratgan", "muallif", "isming", "dasturchi"]
                if any(w in user_text.lower() for w in bot_keywords):
                    if AUTHOR not in final_text:
                        final_text += f"\n\n---\n🤖 <b>Meni {AUTHOR} yaratgan ✨</b>"
                        
                await message.answer(final_text)
            except Exception as e:
                logging.error(f"Suhbat xatosi: {e}")
                await message.answer("❌ Aloqada uzilish bo'ldi, qaytadan yozib ko'ring.")

async def main():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f: f.write("")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
