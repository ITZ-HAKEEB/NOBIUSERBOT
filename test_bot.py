import asyncio
import os
import aiosqlite
import config

async def test_suite():
    print("🧪 Running Self ID Tagger Bot Verification Suite...")
    test_db = "test_tagger.db"
    config.DATABASE_PATH = test_db

    from database.db import (
        init_db,
        add_or_update_user,
        set_user_session,
        get_user,
        remove_user_session,
        get_all_users_with_sessions,
        get_total_users,
        start_tagging_db,
        is_tagging_active_db,
        stop_tagging_db,
        save_login_state,
        get_login_state,
        clear_login_state
    )
    from core.client_manager import client_manager
    from core.tagger import tagger_engine

    # 1. DB Init
    await init_db()
    assert os.path.exists(test_db), "Database file was not created!"
    print("✓ Database initialization passed")

    # 2. Add user
    await add_or_update_user(1234567, "TestUser", "testusername")
    user = await get_user(1234567)
    assert user is not None and user["first_name"] == "TestUser", "Failed to retrieve user!"
    print("✓ User insert and fetch passed")

    # 3. Add session
    await set_user_session(1234567, "test_session_string_abc", 9999999, "SelfBotAccount", "self_uname")
    user_with_session = await get_user(1234567)
    assert user_with_session["string_session"] == "test_session_string_abc", "Session string not saved!"
    assert user_with_session["self_user_id"] == 9999999, "Self user ID not saved!"
    
    sessions = await get_all_users_with_sessions()
    assert len(sessions) == 1, "Expected 1 active session user!"
    print("✓ Session assignment and querying passed")

    # 4. Interactive login state machine
    await save_login_state(1234567, "+1234567890", "hash123", "WAITING_OTP")
    st = await get_login_state(1234567)
    assert st["step"] == "WAITING_OTP" and st["phone_code_hash"] == "hash123"
    await clear_login_state(1234567)
    st2 = await get_login_state(1234567)
    assert st2 is None, "Login state was not cleared!"
    print("✓ Interactive login state machine passed")

    # 5. Tagging state
    await start_tagging_db(-100123456789, 1234567, 9999999)
    active = await is_tagging_active_db(-100123456789)
    assert active is True, "Tagging should be active"

    await stop_tagging_db(-100123456789)
    active_after = await is_tagging_active_db(-100123456789)
    assert active_after is False, "Tagging should be inactive after stop"
    print("✓ Tagging state tracking passed")

    # 6. Session removal
    await remove_user_session(1234567)
    user_after_removal = await get_user(1234567)
    assert user_after_removal["string_session"] is None, "Session string was not removed!"
    print("✓ Session removal passed")

    # 7. Core modules check
    assert client_manager is not None
    assert tagger_engine is not None
    print("✓ Core client manager and tagger engine instances verified")

    # Cleanup test db
    if os.path.exists(test_db):
        os.remove(test_db)
    print("\n🎉 ALL 7 TEST CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(test_suite())
