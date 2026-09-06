#!/usr/bin/env python3
"""
Pyrogram v2 String Session Generator
Run this script locally to quickly generate a session string for your Telegram Self ID account.
"""

import asyncio
from pyrogram import Client

async def generate():
    print("=" * 60)
    print("🚀 Telegram Pyrogram v2 String Session Generator")
    print("=" * 60)
    print("You can get API_ID & API_HASH from https://my.telegram.org\n")

    api_id_str = input("Enter API_ID: ").strip()
    api_hash = input("Enter API_HASH: ").strip()

    if not api_id_str.isdigit() or not api_hash:
        print("❌ Invalid API_ID or API_HASH.")
        return

    api_id = int(api_id_str)

    print("\nConnecting to Telegram MTProto...")
    async with Client(name="session_gen", api_id=api_id, api_hash=api_hash, in_memory=True) as client:
        session_string = await client.export_session_string()
        me = await client.get_me()

        print("\n" + "=" * 60)
        print(f"🎉 Successfully Generated Session for {me.first_name} (@{me.username or me.id})!")
        print("=" * 60)
        print("\nHere is your Pyrogram String Session (keep this secret!):\n")
        print(session_string)
        print("\n" + "=" * 60)
        print("You can copy this string and use /login in your bot, or add to DEFAULT_STRING_SESSION in .env")

if __name__ == "__main__":
    asyncio.run(generate())
