import json
import logging
import os       #needs a function that allows OMI to update clients on their orders ex.. ur order is on the way, Delivered.
import asyncio  #needs real products
import re
import telegram
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler,
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load the bot token from environment variable or replace with your token
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7879235294:AAGlc8j2ywcIhWhHTH6nEBtELST0CiNklYI')  # Ensure this is updated

if not TOKEN or TOKEN == 'YOUR_TELEGRAM_BOT_TOKEN':
    logger.error("Bot token not found. Please set the TELEGRAM_BOT_TOKEN environment variable.")
    exit(1)

# Replace with the actual ID of your group chat
GROUP_CHAT_ID = '-1002355520600'  # e.g., '-1234567890'

# Replace with the actual Telegram ID of the admin
ADMIN_TELEGRAM_ID = '-1002355520600'  # e.g., '123456789'

# File paths for storing data
PRODUCTS_FILE = 'Products.json'
FAVORITES_FILE = 'Favorites.json'
ORDERS_FILE = 'Orders.json'
USERS_FILE = 'Users.json'

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"Chat ID: `{chat_id}`", parse_mode='Markdown')


# Load products from JSON file
def load_products():
    try:
        with open(PRODUCTS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


# Save products to JSON file
def save_products(products):
    with open(PRODUCTS_FILE, 'w') as f:
        json.dump(products, f)


# Load favorites from JSON file
def load_favorites():
    try:
        with open(FAVORITES_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


# Save favorites to JSON file
def save_favorites(favorites):
    with open(FAVORITES_FILE, 'w') as f:
        json.dump(favorites, f)


# Load orders from JSON file
def load_orders():
    try:
        with open(ORDERS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


# Save orders to JSON file
def save_orders(orders):
    with open(ORDERS_FILE, 'w') as f:
        json.dump(orders, f)


# Load users from JSON file
def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


# Save users to JSON file
def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)


# Load data
PRODUCTS = load_products()
FAVORITES = load_favorites()
ORDERS = load_orders()
USERS = load_users()

# Conversation states
CHOOSING_DELIVERY, ENTERING_ADDRESS, SEARCHING = range(3)
REGISTERING_NAME, REGISTERING_PHONE, REGISTERING_ADDRESS = range(3, 6)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user

    # Improved main menu layout with emojis and clearer labels
    keyboard = [
        [InlineKeyboardButton("✨ Shop", callback_data="view_products"), InlineKeyboardButton("👀 Profile", callback_data="view_profile")],
        [InlineKeyboardButton("🛒 Cart", callback_data="view_cart"), InlineKeyboardButton("📦 Orders", callback_data="view_orders")],
        [InlineKeyboardButton("🔍 Search", callback_data="search_products"), InlineKeyboardButton("❤️ Favorites", callback_data="view_favorites")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        f"Hi {user.mention_html()}! Welcome to our shop.\n\n"
        "🛍 **What would you like to do today?**\n\n"
        "Use the buttons below to navigate."
    )

    await update.message.reply_html(
        welcome_text,
        reply_markup=reply_markup
    )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the main menu."""
    if update.callback_query:
        await update.callback_query.answer()
        method = update.callback_query.edit_message_text
    else:
        method = update.message.reply_text

    # Re-use the improved main menu layout
    keyboard = [
        [InlineKeyboardButton("✨ Add", callback_data="view_products"), InlineKeyboardButton("👀 Manage", callback_data="view_profile")],
        [InlineKeyboardButton("🛒 Cart", callback_data="view_cart"), InlineKeyboardButton("📦 Orders", callback_data="view_orders")],
        [InlineKeyboardButton("🔍 Search", callback_data="search_products"), InlineKeyboardButton("❤️ Favorites", callback_data="view_favorites")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await method(
        "🛍 **Main Menu**\n\nPlease choose an option:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def create_button_layout(buttons, columns):
    return [buttons[i:i + columns] for i in range(0, len(buttons), columns)]

# 1. Product Categories

async def view_products_by_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display products in the selected category."""
    query = update.callback_query
    await query.answer()

    # Extract the brand and category from the callback data
    data = query.data[len('category_'):]
    brand, category = data.split('_', 1)

    products = PRODUCTS[brand][category]

    if not products:
        await query.edit_message_text(
            f"No products found in '{category}'.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back to Categories", callback_data=f"brand_{brand}")],
                [InlineKeyboardButton("⬅️ Back to Brands", callback_data="view_products")]
            ])
        )
        return

    # Build the keyboard to display products
    buttons = [
        InlineKeyboardButton(
            f"{product['name']}",
            callback_data=f"product_{product['item_code']}"
        ) for product in products
    ]
    keyboard = create_button_layout(buttons, columns=2)
    keyboard.append([InlineKeyboardButton("⬅️ Back to Categories", callback_data=f"brand_{brand}")])
    keyboard.append([InlineKeyboardButton("⬅️ Back to Brands", callback_data="view_products")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=f"🛍️ **Products in '{category}':**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def view_categories_by_brand(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display categories under a selected brand."""
    query = update.callback_query
    await query.answer()

    # Extract the selected brand from the callback data
    brand = query.data[len('brand_'):]
    categories = sorted(PRODUCTS[brand].keys())

    # Build the keyboard to display categories
    buttons = [
        InlineKeyboardButton(f"{category}", callback_data=f"category_{brand}_{category}")
        for category in categories
    ]
    keyboard = create_button_layout(buttons, columns=1)
    keyboard.append([InlineKeyboardButton("⬅️ Back to Brands", callback_data="view_products")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=f"🛍️ **Categories under {brand}:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
async def view_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the list of brands."""
    query = update.callback_query
    await query.answer()

    # Extract all the brands (top-level keys from PRODUCTS)
    brands = sorted(PRODUCTS.keys())

    # Build the keyboard to display brands
    buttons = [
        InlineKeyboardButton(brand, callback_data=f"brand_{brand}")
        for brand in brands
    ]
    keyboard = create_button_layout(buttons, columns=2)
    keyboard.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        '🛍️ **Select a brand to view categories:**',
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def view_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the list of favorite products."""
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_favorites = FAVORITES.get(user_id, [])

    if not user_favorites:
        await query.edit_message_text(
            "You don't have any favorite products yet.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu")]])
        )
        return

    keyboard = []
    for product_id in user_favorites:
        product = PRODUCTS.get(product_id)
        if product:  # Ensure the product exists
            keyboard.append([
                InlineKeyboardButton(
                    f"❤️ {product['name']} - ₱{product['price']}",
                    callback_data=f"product_{product_id}"
                )
            ])

    # Add "Add All Favorites to Cart" button
    keyboard.append([InlineKeyboardButton("🛒 Add All Favorites to Cart", callback_data="add_favorites_to_cart")])
    keyboard.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('Your favorite products:', reply_markup=reply_markup)


async def add_favorites_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add all favorite products to the user's cart."""
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_favorites = FAVORITES.get(user_id, [])

    if not user_favorites:
        await query.edit_message_text(
            "You don't have any favorite products to add to the cart.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu")]])
        )
        return

    cart = context.user_data.setdefault('cart', [])
    products_added = []
    for product_id in user_favorites:
        product = PRODUCTS.get(product_id)
        if product:
            cart.append(product)
            products_added.append(product['name'])

    if products_added:
        products_list = ', '.join(products_added)
        await query.edit_message_text(
            text=f"🛒 Added your favorite products to the cart:\n{products_list}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 View Cart", callback_data="view_cart")],
                [InlineKeyboardButton("🛍 Continue Shopping", callback_data="view_products")],
                [InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu")]
            ])
        )
    else:
        await query.edit_message_text(
            "None of your favorite products are available to add to the cart.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu")],
                [InlineKeyboardButton("🛍 Continue Shopping", callback_data="view_products")]
            ])
        )


async def product_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, product_id=None) -> None:
    """Handle product selection."""
    query = update.callback_query
    await query.answer()

    if not product_id:
        product_id = query.data[len('item_code'):]

    product = PRODUCTS.get(product_id)
    if not product:
        await query.edit_message_text("Selected product does not exist.")
        return

    user_id = str(query.from_user.id)
    user_favorites = set(FAVORITES.get(user_id, []))
    is_favorite = product_id in user_favorites

    keyboard = [
        [InlineKeyboardButton("💵 Buy Now", callback_data=f"buy_{product_id}")],
        [InlineKeyboardButton("🛒 Add to Cart", callback_data=f"add_to_cart_{product_id}")],
        [InlineKeyboardButton(
            "❌ Remove from Favorites" if is_favorite else "❤️ Add to Favorites",
            callback_data=f"toggle_favorite_{product_id}"
        )],
        [InlineKeyboardButton("⬅️ Back to Products", callback_data="view_products")],
        [InlineKeyboardButton("🛒 View Cart", callback_data="view_cart")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    favorite_status = "❤️ This product is in your favorites." if is_favorite else ""

    await query.edit_message_text(
        text=f"{product['name']}\nPrice: ₱{product['price']}\n\n{product['description']}\n\n{favorite_status}",
        reply_markup=reply_markup
    )


async def toggle_favorite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle a product's favorite status."""
    query = update.callback_query
    await query.answer()

    product_id = query.data[len('toggle_favorite_'):]
    user_id = str(query.from_user.id)

    if user_id not in FAVORITES:
        FAVORITES[user_id] = []

    if product_id in FAVORITES[user_id]:
        FAVORITES[user_id].remove(product_id)
        save_favorites(FAVORITES)
        await query.edit_message_text(
            text=f"❌ Removed '{PRODUCTS[product_id]['name']}' from your favorites."
        )
    else:
        FAVORITES[user_id].append(product_id)
        save_favorites(FAVORITES)
        await query.edit_message_text(
            text=f"✅ Added '{PRODUCTS[product_id]['name']}' to your favorites."
        )

    # Delay to allow the user to see the feedback message
    await asyncio.sleep(2)

    # Return to the product view
    await product_callback(update, context, product_id=product_id)


async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a product to the user's cart."""
    query = update.callback_query
    await query.answer()

    product_id = query.data[len('add_to_cart_'):]
    product = PRODUCTS.get(product_id)
    if not product:
        await query.edit_message_text("Selected product does not exist.")
        return

    cart = context.user_data.setdefault('cart', [])
    cart.append(product)

    await query.edit_message_text(
        text=f"🛒 '{product['name']}' has been added to your cart.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛍 Continue Shopping", callback_data="view_products")],
            [InlineKeyboardButton("🛒 View Cart", callback_data="view_cart")]
        ])
    )


async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the user's cart."""
    query = update.callback_query
    await query.answer()

    cart = context.user_data.get('cart', [])
    if not cart:
        await query.edit_message_text(
            text="Your cart is empty.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛍 Continue Shopping", callback_data="view_products")],
                [InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu")]
            ])
        )
        return

    text = "🛒 **Your Cart:**\n\n"
    total_price = 0
    keyboard = []
    for idx, product in enumerate(cart):
        text += f"{idx + 1}. {product['name']} - ₱{product['price']}\n"
        total_price += float(product['price'])
        keyboard.append([
            InlineKeyboardButton(
                f"❌ Remove '{product['name']}'", callback_data=f"remove_from_cart_{idx}"
            )
        ])
    text += f"\n**Total:** ₱{total_price:.2f}"
    keyboard.append([InlineKeyboardButton("💳 Checkout", callback_data="checkout_cart")])
    keyboard.append([InlineKeyboardButton("🛍 Continue Shopping", callback_data="view_products")])
    keyboard.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def remove_from_cart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove an item from the user's cart."""
    query = update.callback_query
    await query.answer()

    idx_str = query.data[len('remove_from_cart_'):]
    try:
        idx = int(idx_str)
    except ValueError:
        await query.edit_message_text(
            text="Invalid item selected.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 View Cart", callback_data="view_cart")],
                [InlineKeyboardButton("🛍 Continue Shopping", callback_data="view_products")]
            ])
        )
        return

    cart = context.user_data.get('cart', [])

    if 0 <= idx < len(cart):
        removed_product = cart.pop(idx)
        await query.edit_message_text(
            text=f"✅ Removed '{removed_product['name']}' from your cart.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 View Cart", callback_data="view_cart")],
                [InlineKeyboardButton("🛍 Continue Shopping", callback_data="view_products")]
            ])
        )
    else:
        await query.edit_message_text(
            text="Invalid item selected.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 View Cart", callback_data="view_cart")],
                [InlineKeyboardButton("🛍 Continue Shopping", callback_data="view_products")]
            ])
        )


async def checkout_cart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Initiate the checkout process for the cart."""
    query = update.callback_query
    await query.answer()

    cart = context.user_data.get('cart', [])
    if not cart:
        await query.edit_message_text(
            text="Your cart is empty.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛍 Continue Shopping", callback_data="view_products")],
                [InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu")]
            ])
        )
        return ConversationHandler.END

    context.user_data['current_products'] = cart
    context.user_data['is_bulk'] = True  # Indicate bulk order

    keyboard = [
        [InlineKeyboardButton("🚚 Delivery", callback_data="delivery_cart")],
        [InlineKeyboardButton("📦 Pickup", callback_data="pickup_cart")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    total_price = sum(float(product['price']) for product in cart)
    product_names = ', '.join(product['name'] for product in cart)

    await query.edit_message_text(
        text=f"You're about to purchase:\n{product_names}\nTotal: ₱{total_price:.2f}\n"
             f"Would you like delivery or pickup?",
        reply_markup=reply_markup
    )

    return CHOOSING_DELIVERY


async def buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle buy button press."""
    query = update.callback_query
    await query.answer()

    product_id = query.data[len('buy_'):]
    product = PRODUCTS.get(product_id)
    if not product:
        await query.edit_message_text("Selected product does not exist.")
        return ConversationHandler.END

    context.user_data['current_product'] = product

    keyboard = [
        [InlineKeyboardButton("🚚 Delivery", callback_data="delivery")],
        [InlineKeyboardButton("📦 Pickup", callback_data="pickup")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=f"You've selected {product['name']} for ₱{product['price']}.\n"
             f"Would you like delivery or pickup?",
        reply_markup=reply_markup
    )

    return CHOOSING_DELIVERY


# 2. User Registration and Profiles

async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the registration process."""
    await update.message.reply_text("Welcome! Let's set up your profile.\nPlease enter your full name:")
    return REGISTERING_NAME


async def register_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Collect the user's name."""
    user_id = str(update.effective_user.id)
    USERS[user_id] = {'name': update.message.text}
    save_users(USERS)
    await update.message.reply_text("Please enter your phone number:")
    return REGISTERING_PHONE


async def register_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Collect the user's phone number."""
    user_id = str(update.effective_user.id)
    USERS[user_id]['phone'] = update.message.text
    save_users(USERS)
    await update.message.reply_text("Please enter your default delivery address:")
    return REGISTERING_ADDRESS


async def register_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Collect the user's address."""
    user_id = str(update.effective_user.id)
    USERS[user_id]['address'] = update.message.text
    save_users(USERS)
    await update.message.reply_text(
        "Registration complete! You can now place orders more easily. Click /start to place an order.")
    return ConversationHandler.END


async def view_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display the user's profile or start registration if not set."""
    query = update.callback_query
    user_id = str(query.from_user.id)
    user_profile = USERS.get(user_id)

    if not user_profile or 'name' not in user_profile or 'phone' not in user_profile:
        # User is not registered; start registration process
        await query.answer()
        await query.edit_message_text(
            text="You haven't set up a profile yet. Let's set it up now.\n\nPlease enter your full name:"
        )
        return REGISTERING_NAME
    else:
        # User is registered; display profile
        name = user_profile['name']
        phone = user_profile['phone']
        address = user_profile.get('address', 'Not set')
        text = f"**Your Profile:**\n\nName: {name}\nPhone: {phone}\nAddress: {address}"

        keyboard = [
            [InlineKeyboardButton("✏️ Update Profile", callback_data="update_profile")],
            [InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return ConversationHandler.END


async def update_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the profile update process."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="Let's update your profile.\n\nPlease enter your new full name:"
    )
    return REGISTERING_NAME


# Adjusted ordering functions to accommodate manual payment

async def choose_delivery_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle delivery method choice."""
    query = update.callback_query
    await query.answer()

    choice = query.data

    if 'cart' in choice:
        products = context.user_data['current_products']
        is_bulk = True
    elif 'all' in choice:
        products = context.user_data['current_products']
        is_bulk = True
    else:
        product = context.user_data['current_product']
        products = [product]
        is_bulk = False

    if 'pickup' in choice:
        # Process pickup order
        await process_order(update, context, products, 'pickup', is_bulk)
        # Clear cart if checking out cart
        if 'cart' in choice:
            context.user_data['cart'] = []
        return ConversationHandler.END
    elif 'delivery' in choice:
        # Ask for address
        context.user_data['is_bulk'] = is_bulk
        if 'cart' in choice:
            context.user_data['from_cart'] = True
        return await ask_for_address(update, context)
    else:
        await menu(update, context)
        return ConversationHandler.END


async def ask_for_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt the user to enter their delivery address."""
    user_id = str(update.effective_user.id)
    user_profile = USERS.get(user_id, {})
    default_address = user_profile.get('address')

    if default_address:
        keyboard = [
            [InlineKeyboardButton("🏠 Use Default Address", callback_data="use_default_address")],
            [InlineKeyboardButton("📝 Enter New Address", callback_data="enter_new_address")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            text="Would you like to use your default delivery address?",
            reply_markup=reply_markup
        )
        return ENTERING_ADDRESS
    else:
        await update.callback_query.edit_message_text(
            text="Please enter your delivery address:"
        )
        return ENTERING_ADDRESS


async def prompt_new_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt the user to enter a new delivery address."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="Please enter your new delivery address:"
    )
    return ENTERING_ADDRESS


async def enter_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle address input for delivery."""
    user_id = str(update.effective_user.id)
    is_bulk = context.user_data.get('is_bulk', False)
    from_cart = context.user_data.get('from_cart', False)

    if update.callback_query and update.callback_query.data == 'use_default_address':
        # Use default address
        user_profile = USERS.get(user_id)
        if user_profile and 'address' in user_profile:
            address = user_profile['address']
        else:
            # No default address set
            await update.callback_query.edit_message_text(
                "You don't have a default address set. Please enter your delivery address:"
            )
            return ENTERING_ADDRESS
    else:
        # Receive new address from user input
        address = update.message.text
        # Update user's address in the database
        if user_id not in USERS:
            USERS[user_id] = {}
        USERS[user_id]['address'] = address
        save_users(USERS)

    if is_bulk:
        products = context.user_data['current_products']
    else:
        products = [context.user_data['current_product']]

    # Process delivery order
    await process_order(update, context, products, 'delivery', is_bulk, address)

    # Clear cart if checking out cart
    if from_cart:
        context.user_data['cart'] = []
        context.user_data.pop('from_cart', None)

    return ConversationHandler.END


async def process_order(update: Update, context: ContextTypes.DEFAULT_TYPE, products, method, is_bulk, address=None):
    """Process the order and save it."""
    user_id = str(update.effective_user.id)
    if user_id not in ORDERS:
        ORDERS[user_id] = []

    order = {
        'products': products,
        'method': method,
        'user_id': user_id,
        'address': address,
        'status': 'Pending'
    }

    ORDERS[user_id].append(order)
    save_orders(ORDERS)

    total_price = sum(float(product['price']) for product in products)
    product_names = ', '.join(product['name'] for product in products)

    # Payment details
    bank_details = "Bank Account: 1234567890\nAccount Name: Your Name\nBank: Your Bank Name"
    gcash_details = "GCash Number: 09123456789\nAccount Name: Your Name"

    message = (
        f"🛒 **Order Summary:**\n"
        f"Products: {product_names}\n"
        f"Total Price: ₱{total_price:.2f}\n"
        f"Payment Method: {method.capitalize()}\n"
    )

    if method == 'delivery':
        message += f"Delivery Address: {address}\n"

    message += (
        f"\nPlease proceed to payment using the following details:\n\n"
        f"{bank_details}\n\n"
        f"or\n\n"
        f"{gcash_details}\n\n"
        f"After payment, please send a screenshot of the transaction here."
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(message, parse_mode='Markdown')
    else:
        await update.message.reply_text(message, parse_mode='Markdown')

    await send_order_to_group(context, order)


async def send_order_to_group(context: ContextTypes.DEFAULT_TYPE, order: dict) -> None:
    """Send order confirmation to the group chat."""
    user_id = order['user_id']
    products = order['products']
    method = order['method']
    address = order.get('address', '')
    status = order.get('status', 'Pending')

    product_details = '\n'.join(f"- {product['name']}: ₱{product['price']}" for product in products)
    total_price = sum(float(product['price']) for product in products)

    message = f"📦 **New Order Received!**\n\n"
    message += f"**User ID:** {user_id}\n"
    message += f"**Products:**\n{product_details}\n"
    message += f"**Total Price:** ₱{total_price:.2f}\n"
    message += f"**Method:** {method.capitalize()}\n"
    if method == 'delivery':
        message += f"**Address:** {address}\n"
    message += f"**Status:** {status}\n"

    await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=message, parse_mode='Markdown')


async def view_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the user's orders."""
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    if user_id not in ORDERS or not ORDERS[user_id]:
        text = "📭 You haven't made any orders yet."
    else:
        text = "📝 **Your Orders:**\n\n"
        for i, order in enumerate(ORDERS[user_id], 1):
            product_names = ', '.join(product['name'] for product in order['products'])
            total_price = sum(float(product['price']) for product in order['products'])
            status = order.get('status', 'Unknown')
            text += f"**Order {i}:**\n"
            text += f"📦 Products: {product_names}\n"
            text += f"💰 Total Price: ₱{total_price:.2f}\n"
            text += f"🚚 Method: {order['method'].capitalize()}\n"
            if order['method'] == 'delivery':
                text += f"🏠 Address: {order['address']}\n"
            text += f"📈 Status: **{status}**\n\n"

    keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')


# --------------------
# Search Functionality
# --------------------

async def search_products_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask the user to enter a search query."""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("❌ Cancel", callback_data="menu")]
    ]

    await query.edit_message_text(
        text="Please enter the product name or keyword you're looking for:",
    )
    return SEARCHING


async def search_products_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display search results based on the user's query."""
    query_text = update.message.text.strip().lower()
    pattern = re.compile(re.escape(query_text), re.IGNORECASE)
    matching_products = {
        product_id: product for product_id, product in PRODUCTS.items()
        if pattern.search(product['name']) or pattern.search(product['description'])
    }

    if not matching_products:
        await update.message.reply_text(
            text="❌ No products found matching your search. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 Try Again", callback_data="search_products")],
                [InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu")]
            ])
        )
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(
            f"{product['name']} - ₱{product['price']}",
            callback_data=f"product_{product_id}"
        )] for product_id, product in matching_products.items()
    ]
    keyboard.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        text="🔍 **Search Results:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return ConversationHandler.END


# --------------------
# Image Handling Functionality
# --------------------

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming photos: forward to admin and confirm to user."""
    user = update.effective_user
    message = update.message

    try:
        # Forward the entire message to the admin
        await message.forward(chat_id=ADMIN_TELEGRAM_ID)

        # Reply to the user
        await message.reply_text("Thank you for your confirmation.")
    except Exception as e:
        logger.error(f"Error forwarding photo: {e}")
        await message.reply_text("⚠️ There was an error processing your photo. Please try again later.")


# --------------------
# Error Handler
# --------------------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and handle specific exceptions."""
    error = context.error
    if isinstance(error, telegram.error.BadRequest) and "Message is not modified" in str(error):
        # Ignore this specific error
        return
    else:
        logger.error(msg="Exception while handling an update:", exc_info=error)
        if isinstance(update, Update) and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "⚠️ An unexpected error occurred. Please try again later."
                )
            except Exception as e:
                logger.error(f"Failed to send error message: {e}")


async def back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the /back command: cancel current conversation and show main menu."""
    if update.message:
        await update.message.reply_text("Operation cancelled. Returning to the main menu.")
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Operation cancelled. Returning to the main menu.")

    keyboard = [
        [InlineKeyboardButton("✨ Add", callback_data="view_products"), InlineKeyboardButton("👀 Manage", callback_data="view_profile")],
        [InlineKeyboardButton("🛒 Cart", callback_data="view_cart"), InlineKeyboardButton("📦 Orders", callback_data="view_orders")],
        [InlineKeyboardButton("🔍 Search", callback_data="search_products"), InlineKeyboardButton("❤️ Favorites", callback_data="view_favorites")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_html(
            "🛍 **Main Menu**\n\nPlease choose an option:",
            reply_markup=reply_markup
        )
    elif update.callback_query:
        await update.callback_query.message.reply_html(
            "🛍 **Main Menu**\n\nPlease choose an option:",
            reply_markup=reply_markup
        )

    return ConversationHandler.END


def main() -> None:
    """Run the bot."""
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(add_favorites_to_cart, pattern="^add_favorites_to_cart$"),
            CallbackQueryHandler(checkout_cart, pattern="^checkout_cart$"),
            CallbackQueryHandler(buy_callback, pattern="^buy_.+"),
            CallbackQueryHandler(search_products_start, pattern="^search_products$"),
            CommandHandler("register", start_registration),
            CallbackQueryHandler(view_profile, pattern="^view_profile$"),
            CallbackQueryHandler(update_profile, pattern="^update_profile$"),
        ],
        states={
            CHOOSING_DELIVERY: [
                CallbackQueryHandler(choose_delivery_method, pattern="^(delivery|pickup)$"),
                CallbackQueryHandler(choose_delivery_method, pattern="^(delivery_cart|pickup_cart)$"),
            ],
            ENTERING_ADDRESS: [
                CallbackQueryHandler(enter_address, pattern="^use_default_address$"),
                CallbackQueryHandler(prompt_new_address, pattern="^enter_new_address$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_address)
            ],
            SEARCHING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_products_result)
            ],
            REGISTERING_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, register_name)
            ],
            REGISTERING_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, register_phone)
            ],
            REGISTERING_ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, register_address)
            ],
        },
        fallbacks=[
            CallbackQueryHandler(menu, pattern="^menu$"),
            CommandHandler("start", start),
        ],
        per_user=True,
        per_chat=False,
    )

    application.add_error_handler(error_handler)

    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(CommandHandler("back", back))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(menu, pattern="^menu$"))
    application.add_handler(CallbackQueryHandler(view_products, pattern="^view_products$"))
    application.add_handler(CallbackQueryHandler(view_categories_by_brand, pattern="^brand_.+"))
    application.add_handler(CallbackQueryHandler(view_products_by_category, pattern="^category_.+"))
    application.add_handler(CallbackQueryHandler(add_to_cart, pattern="^add_to_cart_.+"))
    application.add_handler(CallbackQueryHandler(view_cart, pattern="^view_cart$"))
    application.add_handler(CallbackQueryHandler(remove_from_cart, pattern="^remove_from_cart_.+"))
    application.add_handler(CallbackQueryHandler(view_favorites, pattern="^view_favorites$"))
    application.add_handler(CallbackQueryHandler(product_callback, pattern="^product_.+"))
    application.add_handler(CallbackQueryHandler(toggle_favorite, pattern="^toggle_favorite_.+"))
    application.add_handler(CallbackQueryHandler(view_orders, pattern="^view_orders$"))
    application.add_handler(CallbackQueryHandler(add_to_cart, pattern="^add_to_cart_.+"))
    application.add_handler(CallbackQueryHandler(view_cart, pattern="^view_cart$"))
    application.add_handler(CallbackQueryHandler(remove_from_cart, pattern="^remove_from_cart_.+"))
    application.add_handler(CommandHandler("get_id", get_id))

    application.run_polling()


if __name__ == '__main__':
    main()
