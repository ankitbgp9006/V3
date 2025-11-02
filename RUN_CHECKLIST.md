
# RUN CHECKLIST (Auto-generated 2025-11-02T18:19:19.988392Z)

1) Python 3.9+ (3.10 OK). If 3.8/3.9, annotations are patched.
2) Env Vars required:
   - API_ID, API_HASH, BOT_TOKEN, OWNER_ID
   - DATABASE_URL  (Mongo URI)
3) Telegram:
   - Bot must be ADMIN in target group/channel.
   - For forum threads: Supergroup + Enable Topics + "Manage Topics" permission.
4) Quick test:
   - /health   -> OK should respond with bot & chat.
   - /start    -> Should reply.
   - /drm      -> Send a tiny .txt with 1-2 links first.
5) On success:
   - Auto Topic (from (Topic)), Caption sections, Auto Index after uploads.
   - Index saved to Mongo 'topic_indexes' and JSON file.
