import asyncio
from aiogram import Dispatcher, Bot, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder
import db_manager as db

HEAD, TORSO, LEGS = "ГОЛОВА", "КОРПУС", "НОГИ"

TOKEN = '8218911442:AAHNqm6YfgViFAOc18q1nMb07DfnUqS-OzY'
BOT = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
DP = Dispatcher()

def kb_choose_player(session_id):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Игрок 1", callback_data=f"role_1_{session_id}"))
    builder.add(InlineKeyboardButton(text="Игрок 2", callback_data=f"role_2_{session_id}"))
    return builder.as_markup()

def kb_zones(session_id, player_num, is_attacker):
    builder = InlineKeyboardBuilder()
    role = "АТАКА" if is_attacker else "ЗАЩИТА"
    for zone in [HEAD, TORSO, LEGS]:
        builder.add(InlineKeyboardButton(text=f"{role}: {zone}", callback_data=f"act_{player_num}_{session_id}_{zone}"))
    return builder.adjust(1).as_markup()

@DP.message(Command('start'))
async def cmd_start(message: Message, command: CommandObject):
    session_id = command.args
    if not session_id:
        await message.answer("Введите код из игры: <code>/start 123456</code>")
        return
    await message.answer(f"Сессия {session_id}. Кто вы?", reply_markup=kb_choose_player(session_id))

@DP.callback_query(F.data.startswith('role_'))
async def cb_role(callback: CallbackQuery):
    _, p_num, s_id = callback.data.split('_')
    data = db.get_session_data(s_id)
    if not data:
        await callback.answer("Сессия не найдена в БД")
        return
    is_atk = (p_num == '1' and data['attacker_side'] == 'left') or (p_num == '2' and data['attacker_side'] == 'right')
    await callback.message.edit_text(f"Вы — Игрок {p_num}. Ваш ход:", reply_markup=kb_zones(s_id, p_num, is_atk))

@DP.callback_query(F.data.startswith('act_'))
async def cb_action(callback: CallbackQuery):
    _, p_num, s_id, zone = callback.data.split('_')
    if db.set_choice(s_id, int(p_num), zone):
        await callback.message.edit_text(f"Выбрано: {zone}. Ждите анимации.")
    else:
        await callback.answer("Выбор уже сделан!")

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # handle_signals=False обязателен для Mac/Linux в потоке
    loop.run_until_complete(DP.start_polling(BOT, handle_signals=False))