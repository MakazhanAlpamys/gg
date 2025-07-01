import os
import json
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters, ConversationHandler, PicklePersistence
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Здесь укажите ID пользователя, который будет администратором
DEFAULT_ADMIN_ID = "858908158"  # Замените на реальный Telegram ID администратора

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for the conversation
SELECTING_ADDRESS, VIEWING_PRODUCTS, SENDING_ORDER, WAITING_FOR_ADDRESS = range(4)
# Admin states
ADMIN_MENU, ADMIN_ADD_ADDRESS, ADMIN_REMOVE_ADDRESS, ADMIN_UPDATE_PRODUCTS = range(4, 8)

# File paths for storing data
DATA_DIR = "data"
ADDRESSES_FILE = os.path.join(DATA_DIR, "addresses.json")
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
ADMINS_FILE = os.path.join(DATA_DIR, "admins.json")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Initialize data files if they don't exist
def initialize_data_files():
    # Initialize addresses
    if not os.path.exists(ADDRESSES_FILE):
        with open(ADDRESSES_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False)
    
    # Initialize products
    if not os.path.exists(PRODUCTS_FILE):
        with open(PRODUCTS_FILE, 'w', encoding='utf-8') as f:
            json.dump("Список товаров пуст. Админ должен обновить список.", f, ensure_ascii=False)
    
    # Initialize admins with default admin
    if not os.path.exists(ADMINS_FILE):
        with open(ADMINS_FILE, 'w', encoding='utf-8') as f:
            json.dump([DEFAULT_ADMIN_ID], f, ensure_ascii=False)
    else:
        # Ensure the default admin is in the list
        admins = load_admins()
        if DEFAULT_ADMIN_ID not in admins:
            admins.append(DEFAULT_ADMIN_ID)
            save_admins(admins)

# Load data from files
def load_addresses():
    with open(ADDRESSES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_products():
    with open(PRODUCTS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_admins():
    with open(ADMINS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

# Save data to files
def save_addresses(addresses):
    with open(ADDRESSES_FILE, 'w', encoding='utf-8') as f:
        json.dump(addresses, f, ensure_ascii=False)

def save_products(products):
    with open(PRODUCTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False)

def save_admins(admins):
    with open(ADMINS_FILE, 'w', encoding='utf-8') as f:
        json.dump(admins, f, ensure_ascii=False)

# Function to check if user is admin
def is_admin(user_id):
    admins = load_admins()
    return str(user_id) in admins

# Command handlers
def start(update: Update, context: CallbackContext):
    # Сбрасываем состояние беседы
    if hasattr(context, 'user_data'):
        context.user_data.clear()
    
    user = update.effective_user
    
    if is_admin(user.id):
        # Admin menu
        keyboard = [
            [KeyboardButton("👤 Пользовательский режим")],
            [KeyboardButton("➕ Добавить ЖК"), KeyboardButton("➖ Удалить ЖК")],
            [KeyboardButton("📝 Обновить список товаров")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        update.message.reply_text(
            f"Админ-панель",
            reply_markup=reply_markup
        )
        return ADMIN_MENU
    else:
        # User menu - show available addresses
        addresses = load_addresses()
        
        if not addresses:
            update.message.reply_text("В данный момент нет доступных ЖК. Пожалуйста, обратитесь к администратору.")
            return ConversationHandler.END
        
        keyboard = []
        for address in addresses:
            keyboard.append([InlineKeyboardButton(address, callback_data=f"address_{address}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            f"Выберите ваш ЖК:",
            reply_markup=reply_markup
        )
        return SELECTING_ADDRESS

# Address selection handler
def address_selected(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    # Extract address from callback data
    selected_address = query.data.replace("address_", "")
    context.user_data["selected_address"] = selected_address
    
    # Show products list
    products = load_products()
    query.edit_message_text(
        f"ЖК: {selected_address}\n\n"
        f"{products}\n\n"
        "Отправьте сообщение с заказом:"
    )
    
    return SENDING_ORDER

# Order message handler
def receive_order(update: Update, context: CallbackContext):
    context.user_data["order"] = update.message.text
    
    update.message.reply_text(
        "Укажите точный адрес (квартира, подъезд, номер телефона):"
    )
    
    return WAITING_FOR_ADDRESS

# Address details handler
def receive_address_details(update: Update, context: CallbackContext):
    context.user_data["address_details"] = update.message.text
    
    # Send order to courier group
    selected_address = context.user_data.get("selected_address", "Не указан")
    order = context.user_data.get("order", "Не указан")
    address_details = context.user_data.get("address_details", "Не указан")
    
    order_message = (
        f"📦 Новый заказ!\n"
        f"🏠 ЖК: {selected_address}\n"
        f"🛒 Заказ: {order}\n"
        f"📍 Детали адреса: {address_details}\n"
        f"👤 Заказчик: {update.effective_user.first_name} (@{update.effective_user.username})"
    )
    
    # Get courier group chat ID from environment variable
    courier_group_id = os.getenv("COURIER_GROUP_ID")
    if courier_group_id:
        try:
            context.bot.send_message(chat_id=courier_group_id, text=order_message)
        except Exception as e:
            logger.error(f"Failed to send message to courier group: {e}")
            update.message.reply_text("Произошла ошибка при отправке заказа курьерам.")
    
    update.message.reply_text(
        "Заказ отправлен курьерам."
    )
    
    # Очищаем данные сессии
    context.user_data.clear()
    return ConversationHandler.END

# Admin handlers
def admin_menu(update: Update, context: CallbackContext):
    text = update.message.text
    
    if text == "👤 Пользовательский режим":
        # Switch to user mode
        return start(update, context)
    elif text == "➕ Добавить ЖК":
        update.message.reply_text("Введите название ЖК:")
        return ADMIN_ADD_ADDRESS
    elif text == "➖ Удалить ЖК":
        addresses = load_addresses()
        
        if not addresses:
            update.message.reply_text("Список ЖК пуст.")
            return ADMIN_MENU
        
        keyboard = []
        for address in addresses:
            keyboard.append([InlineKeyboardButton(address, callback_data=f"remove_{address}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            "Выберите ЖК для удаления:",
            reply_markup=reply_markup
        )
        return ADMIN_REMOVE_ADDRESS
    elif text == "📝 Обновить список товаров":
        current_products = load_products()
        update.message.reply_text(
            f"Текущий список товаров:\n{current_products}\n\n"
            "Отправьте новый список товаров:"
        )
        return ADMIN_UPDATE_PRODUCTS
    else:
        keyboard = [
            [KeyboardButton("👤 Пользовательский режим")],
            [KeyboardButton("➕ Добавить ЖК"), KeyboardButton("➖ Удалить ЖК")],
            [KeyboardButton("📝 Обновить список товаров")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        update.message.reply_text(
            "Выберите действие:", 
            reply_markup=reply_markup
        )
        return ADMIN_MENU

def add_address(update: Update, context: CallbackContext):
    new_address = update.message.text
    addresses = load_addresses()
    
    if len(addresses) >= 99999999999:
        update.message.reply_text("Достигнут максимум (99999999999 ЖК). Удалите существующий ЖК.")
    elif new_address in addresses:
        update.message.reply_text(f"ЖК '{new_address}' уже существует.")
    else:
        addresses.append(new_address)
        save_addresses(addresses)
        update.message.reply_text(f"ЖК '{new_address}' добавлен.")
    
    # Return to admin menu
    keyboard = [
        [KeyboardButton("👤 Пользовательский режим")],
        [KeyboardButton("➕ Добавить ЖК"), KeyboardButton("➖ Удалить ЖК")],
        [KeyboardButton("📝 Обновить список товаров")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text("Админ-панель", reply_markup=reply_markup)
    
    return ADMIN_MENU

def remove_address_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    # Extract address from callback data
    address_to_remove = query.data.replace("remove_", "")
    addresses = load_addresses()
    
    if address_to_remove in addresses:
        addresses.remove(address_to_remove)
        save_addresses(addresses)
        query.edit_message_text(f"ЖК '{address_to_remove}' удален.")
    else:
        query.edit_message_text(f"ЖК '{address_to_remove}' не найден.")
    
    # Return to admin menu
    keyboard = [
        [KeyboardButton("👤 Пользовательский режим")],
        [KeyboardButton("➕ Добавить ЖК"), KeyboardButton("➖ Удалить ЖК")],
        [KeyboardButton("📝 Обновить список товаров")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Админ-панель",
        reply_markup=reply_markup
    )
    
    return ADMIN_MENU

def update_products(update: Update, context: CallbackContext):
    new_products = update.message.text
    save_products(new_products)
    update.message.reply_text("Список товаров обновлен.")
    
    # Return to admin menu
    keyboard = [
        [KeyboardButton("👤 Пользовательский режим")],
        [KeyboardButton("➕ Добавить ЖК"), KeyboardButton("➖ Удалить ЖК")],
        [KeyboardButton("📝 Обновить список товаров")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text("Админ-панель", reply_markup=reply_markup)
    
    return ADMIN_MENU

def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("Операция отменена.")
    context.user_data.clear()
    return ConversationHandler.END

def error_handler(update, context):
    logger.warning(f'Update "{update}" caused error "{context.error}"')

def main():
    # Initialize data files
    initialize_data_files()
    
    # Create the Updater and dispatcher
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
        return
    
    updater = Updater(token)
    dispatcher = updater.dispatcher
    
    # Add conversation handler for users
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECTING_ADDRESS: [CallbackQueryHandler(address_selected, pattern=r'^address_')],
            SENDING_ORDER: [MessageHandler(Filters.text & ~Filters.command, receive_order)],
            WAITING_FOR_ADDRESS: [MessageHandler(Filters.text & ~Filters.command, receive_address_details)],
            ADMIN_MENU: [MessageHandler(Filters.text & ~Filters.command, admin_menu)],
            ADMIN_ADD_ADDRESS: [MessageHandler(Filters.text & ~Filters.command, add_address)],
            ADMIN_REMOVE_ADDRESS: [CallbackQueryHandler(remove_address_callback, pattern=r'^remove_')],
            ADMIN_UPDATE_PRODUCTS: [MessageHandler(Filters.text & ~Filters.command, update_products)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    dispatcher.add_handler(conv_handler)
    
    # Add error handler
    dispatcher.add_error_handler(error_handler)
    
    # Start the Bot
    updater.start_polling(allowed_updates=['message', 'callback_query', 'my_chat_member'])
    logger.info("Bot started")
    
    # Run the bot until you press Ctrl-C
    updater.idle()

if __name__ == '__main__':
    main() 