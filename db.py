from datetime import datetime, timedelta
from pymongo import MongoClient
from vars import MONGO_URL, OWNER_ID, ADMINS
import colorama
from colorama import Fore, Style
import time

# Initialize colorama for Windows
colorama.init()

class Database:
    def __init__(self):
        self._print_startup_message()
        try:
            print(f"{Fore.YELLOW}⌛ Connecting to MongoDB...{Style.RESET_ALL}")
            self.client = MongoClient(MONGO_URL)
            # Test connection
            self.client.server_info()
            self.db = self.client['ugdev_db']
            self.users = self.db['users']
            self.settings = self.db['user_settings']  # New collection for settings
            self.topic_indexes = self.db['topic_indexes']  # New collection for topic-wise indexes
            print(f"{Fore.GREEN}✓ MongoDB Connected Successfully!{Style.RESET_ALL}")
            
            print(f"{Fore.YELLOW}⌛ Setting up database...{Style.RESET_ALL}")
            # First, update all existing users without bot_username
            self._migrate_existing_users()
        
            # Then create the index
            try:
                self.users.create_index([("bot_username", 1), ("user_id", 1)], unique=True)
                self.settings.create_index([("user_id", 1)], unique=True)  # Index for settings
                # Add index for expiry date to make cleanup faster
                self.users.create_index("expiry_date")
                print(f"{Fore.GREEN}✓ Database indexes created successfully!{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}⚠ Warning: Could not create index - {str(e)}{Style.RESET_ALL}")
            
            print(f"{Fore.GREEN}✓ Database initialization complete!{Style.RESET_ALL}\n")
            
        except Exception as e:
            print(f"{Fore.RED}✕ Error connecting to MongoDB: {str(e)}{Style.RESET_ALL}")
            raise e
            
    def _print_startup_message(self):
        print(f"\n{Fore.CYAN}{'='*50}")
        print(f"{Fore.CYAN}🚀 UGDEV Uploader Bot - Database Initialization")
        print(f"{'='*50}{Style.RESET_ALL}\n")
            
    def _migrate_existing_users(self):
        """Update existing users to include bot_username field"""
        try:
            self.users.update_many(
                {"bot_username": {"$exists": False}},
                {"$set": {"bot_username": "ugdevbot"}}  # Default bot username
                )
        except Exception as e:
            print(f"{Fore.RED}⚠ Warning: Could not migrate users - {str(e)}{Style.RESET_ALL}")
        
    def get_user(self, user_id: int, bot_username: str = "ugdevbot"):
        """Get user by ID and bot username"""
        try:
            return self.users.find_one({
                "user_id": user_id,
                "bot_username": bot_username
            })
        except Exception as e:
            print(f"Error getting user: {str(e)}")
            return None
        
    def is_user_authorized(self, user_id: int, bot_username: str = "ugdevbot") -> bool:
        """Check if user is authorized and subscription is active"""
        try:
            user = self.get_user(user_id, bot_username)
            if not user:
                return False
            
            # Check if user is admin
            if user_id in ADMINS or user_id == OWNER_ID:
                return True
                
            # Check subscription expiry
            expiry = user.get('expiry_date')
            if not expiry:
                return False
                
            if isinstance(expiry, str):
                expiry = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
                
            return expiry > datetime.now()
            
        except Exception as e:
            print(f"Error checking authorization: {str(e)}")
            return False
        
    def add_user(self, user_id: int, name: str, days: int, bot_username: str = "ugdevbot"):
        """Add or update user with subscription"""
        try:
            expiry_date = datetime.now() + timedelta(days=days)
            
            self.users.update_one(
                {"user_id": user_id, "bot_username": bot_username},
                {
                    "$set": {
                        "name": name,
                        "expiry_date": expiry_date,
                        "added_date": datetime.now()
                    }
                },
                upsert=True
            )
            return True, expiry_date
            
        except Exception as e:
            print(f"Error adding user: {str(e)}")
            return False, None
        
    def remove_user(self, user_id: int, bot_username: str = "ugdevbot"):
        """Remove user from database"""
        try:
            result = self.users.delete_one({
                "user_id": user_id,
                "bot_username": bot_username
            })
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error removing user: {str(e)}")
            return False
        
    def list_users(self, bot_username: str = "ugdevbot"):
        """Get list of all users"""
        try:
            return list(self.users.find({"bot_username": bot_username}))
        except Exception as e:
            print(f"Error listing users: {str(e)}")
            return []

    def is_admin(self, user_id: int) -> bool:
        """Check if a user is admin or owner"""
        try:
            is_admin = user_id == OWNER_ID or user_id in ADMINS
            if is_admin:
                print(f"{Fore.GREEN}✓ User is admin/owner{Style.RESET_ALL}")
            return is_admin
        except Exception as e:
            print(f"Error checking admin status: {str(e)}")
            return False

    def get_user_settings(self, user_id: int):
        """Get user settings"""
        try:
            settings = self.settings.find_one({"user_id": user_id})
            if not settings:
                # Default settings
                settings = {
                    "user_id": user_id,
                    "resolution": "480",  # Default 480p
                    "credit_name": None,  # Default to None
                    "token": None,  # Default to None
                    "thumbnail_url": None,  # Default to None
                    "watermark_text": None,  # Default to None
                    "channel_id": None  # Default to None
                }
                self.settings.insert_one(settings)
            return settings
        except Exception as e:
            print(f"Error getting user settings: {str(e)}")
            return None

    def update_user_settings(self, user_id: int, **kwargs):
        """Update user settings"""
        try:
            # Only update provided fields
            update_data = {k: v for k, v in kwargs.items() if v is not None}
            if update_data:
                self.settings.update_one(
                    {"user_id": user_id},
                    {"$set": update_data},
                    upsert=True
                )
            return True
        except Exception as e:
            print(f"Error updating user settings: {str(e)}")
            return False

    def add_channel(self, channel_id: int, added_by: int, bot_username: str):
        """Add a channel with same expiry as the user who added it"""
        try:
            user = self.get_user(added_by, bot_username)
            if not user:
                return False, "User not found"
                
            channel = self.db.channels.find_one({
                "channel_id": channel_id,
                "bot_username": bot_username
            })
            
            if channel:
                return False, "Channel already exists"
                
            self.db.channels.insert_one({
                "channel_id": channel_id,
                "added_by": added_by,
                "bot_username": bot_username,
                "expiry_date": user['expiry_date'],
                "added_date": datetime.now()
            })
            return True, "Channel added successfully"
        except Exception as e:
            print(f"Error adding channel: {str(e)}")
            return False, str(e)
    
    def is_channel_authorized(self, channel_id: int, bot_username: str):
        """Check if channel is authorized"""
        try:
            channel = self.db.channels.find_one({
                "channel_id": channel_id,
                "bot_username": bot_username
            })
            
            if not channel:
                return False
                
            expiry = channel['expiry_date']
            if isinstance(expiry, str):
                expiry = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
                
            return expiry > datetime.now()
        except Exception:
            return False
    def get_user_channels(self, user_id: int, bot_username: str):
        """Get all channels added by a user"""
        return list(self.db.channels.find({
        "added_by": user_id,
        "bot_username": bot_username
    }))
            
    def get_channel_info(self, channel_id: int, bot_username: str):
        """Get channel information"""
        return self.db.channels.find_one({
            "channel_id": channel_id,
            "bot_username": bot_username
        })

    def remove_channel(self, channel_id: int, bot_username: str):
        """Remove a channel"""
        return self.db.channels.delete_one({
            "channel_id": channel_id,
            "bot_username": bot_username
        })

    def list_bot_usernames(self):
        """Get list of all bot usernames in the database"""
        try:
            # Get distinct bot_username values from users collection
            usernames = self.users.distinct("bot_username")
            return usernames if usernames else ["ugdevbot"]  # Return default if none found
        except Exception as e:
            print(f"Error listing bot usernames: {str(e)}")
            return ["ugdevbot"]  # Return default on error

    def get_log_channel(self, bot_username: str):
        """Get the log channel ID for a specific bot"""
        try:
            settings = self.db.bot_settings.find_one({"bot_username": bot_username})
            if settings and 'log_channel' in settings:
                return settings['log_channel']
            return None
        except Exception as e:
            print(f"Error getting log channel: {str(e)}")
            return None

    def set_log_channel(self, bot_username: str, channel_id: int):
        """Set the log channel ID for a specific bot"""
        try:
            self.db.bot_settings.update_one(
                {"bot_username": bot_username},
                {"$set": {"log_channel": channel_id}},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error setting log channel: {str(e)}")
            return False

    async def cleanup_expired_users(self, bot):
        """Remove expired users and notify them"""
        try:
            current_time = datetime.now()
            # Find all expired users
            expired_users = self.users.find({
                "expiry_date": {"$lt": current_time},
                "user_id": {"$nin": [OWNER_ID] + ADMINS}  # Don't remove admins/owner
            })
            
            removed_count = 0
            for user in expired_users:
                try:
                    # Send notification to user
                    await bot.send_message(
                        user["user_id"],
                        f"**⚠️ Your subscription has expired!**\n\n"
                        f"• Name: {user['name']}\n"
                        f"• Expired on: {user['expiry_date'].strftime('%d-%m-%Y')}\n\n"
                        f"Contact admin to renew your subscription."
                    )
                    
                    # Remove user from database
                    self.users.delete_one({"_id": user["_id"]})
                    removed_count += 1
                    
                    # Log to admin
                    admin_msg = (
                        f"**🚫 Removed Expired User**\n\n"
                        f"• Name: {user['name']}\n"
                        f"• ID: {user['user_id']}\n"
                        f"• Expired on: {user['expiry_date'].strftime('%d-%m-%Y')}"
                    )
                    for admin in ADMINS + [OWNER_ID]:
                        try:
                            await bot.send_message(admin, admin_msg)
                        except:
                            continue
                            
                except Exception as e:
                    print(f"Error processing expired user {user['user_id']}: {str(e)}")
                    continue
                    
            return removed_count
            
        except Exception as e:
            print(f"Error in cleanup: {str(e)}")
            return 0

    def get_user_expiry_info(self, user_id: int, bot_username: str = "ugdevbot"):
        """Get user expiry information"""
        try:
            user = self.get_user(user_id, bot_username)
            if not user:
                return None
                
            expiry = user.get('expiry_date')
            if not expiry:
                return None
                
            if isinstance(expiry, str):
                expiry = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
                
            # Calculate days left
            days_left = (expiry - datetime.now()).days
            
            return {
                "name": user.get('name', 'Unknown'),
                "user_id": user_id,
                "expiry_date": expiry.strftime("%d-%m-%Y"),
                "days_left": days_left
            }
            
        except Exception as e:
            print(f"Error getting expiry info: {str(e)}")
            return None

print(f"\n{Fore.CYAN}{'='*50}")
print(f"🤖 Initializing UGDEV Uploader Bot Database")
print(f"{'='*50}{Style.RESET_ALL}\n")

# Initialize database
try:
    db = Database()
except Exception as e:
    print(f"{Fore.RED}✕ Fatal Error: Could not initialize database{Style.RESET_ALL}")
    raise e