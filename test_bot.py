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
        clear_login_state,
        get_auto_message_settings,
        set_auto_message_text,
        set_auto_message_enabled,
        reset_auto_message_text,
        has_received_auto_message,
        mark_auto_message_sent,
        clear_auto_message_history,
        DEFAULT_AUTO_MESSAGE
    )
    from core.client_manager import client_manager
    from core.tagger import tagger_engine
    from core.automsg import format_auto_message
    from pyrogram.types import User

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

    # 8. Auto Message Settings & Customization
    default_settings = await get_auto_message_settings(9999999)
    assert default_settings["is_enabled"] is True, "Auto message should be enabled by default"
    assert default_settings["message"] == DEFAULT_AUTO_MESSAGE, "Default template mismatch"
    assert default_settings["is_custom"] is False, "Should not be custom initially"

    custom_text = "Hey {name}! Welcome to my DM. I will reply soon."
    await set_auto_message_text(9999999, custom_text)
    updated_settings = await get_auto_message_settings(9999999)
    assert updated_settings["message"] == custom_text, "Custom message text not updated"
    assert updated_settings["is_custom"] is True, "Should be marked as custom"

    await set_auto_message_enabled(9999999, False)
    disabled_settings = await get_auto_message_settings(9999999)
    assert disabled_settings["is_enabled"] is False, "Auto message should be disabled"

    await set_auto_message_enabled(9999999, True)
    await reset_auto_message_text(9999999)
    reset_settings = await get_auto_message_settings(9999999)
    assert reset_settings["message"] == DEFAULT_AUTO_MESSAGE, "Reset message should restore default"
    assert reset_settings["is_custom"] is False
    print("✓ Auto message settings and customization passed")

    # 9. Auto Message History (First-time DM tracking) & Placeholders
    assistant_id = 9999999
    peer_id_1 = 111111
    peer_id_2 = 222222

    # Check peer 1 is first-time
    has_sent_1 = await has_received_auto_message(assistant_id, peer_id_1)
    assert has_sent_1 is False, "Peer 1 should not have received auto-message yet"

    # Mark peer 1 as received
    await mark_auto_message_sent(assistant_id, peer_id_1)
    has_sent_1_after = await has_received_auto_message(assistant_id, peer_id_1)
    assert has_sent_1_after is True, "Peer 1 should now be recorded as greeted"

    # Peer 2 should still be un-greeted
    assert await has_received_auto_message(assistant_id, peer_id_2) is False

    # Test template placeholder formatting
    test_peer = User(id=peer_id_1, first_name="Alice", last_name="Wonder", username="alicew")
    test_assistant = User(id=assistant_id, first_name="BobAssistant")
    formatted = format_auto_message(
        "Hi {name} ({username})! Mention: {mention}. My name is {my_name}.",
        peer=test_peer,
        assistant=test_assistant
    )
    assert "Hi Alice (@alicew)!" in formatted
    assert "[Alice](tg://user?id=111111)" in formatted
    assert "My name is BobAssistant." in formatted

    # Clear greeted history
    cleared_count = await clear_auto_message_history(assistant_id)
    assert cleared_count == 1, f"Expected 1 cleared contact, got {cleared_count}"
    assert await has_received_auto_message(assistant_id, peer_id_1) is False, "History should be cleared"
    print("✓ First-time DM tracking and placeholder formatting passed")

    # Cleanup test db
    if os.path.exists(test_db):
        os.remove(test_db)
    print("\n🎉 ALL 9 TEST CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(test_suite())

