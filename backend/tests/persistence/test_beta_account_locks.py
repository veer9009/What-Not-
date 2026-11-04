from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import User
from app.repositories.users import UserRepository


def test_account_write_guard_allows_recipient_foreign_key_lock(migrated_engine):
    # Non-key account updates must still serialize suspension, while notification
    # recipient FK KEY SHARE locks must not deadlock with another actor's guard.
    with Session(migrated_engine) as seed, seed.begin():
        user=User(name='Lock user',email='lock-guard@example.com',phone='lock-guard',password_hash='test',role='BUYER')
        seed.add(user);seed.flush();user_id=user.id
    with Session(migrated_engine) as writer, writer.begin():
        UserRepository(writer).get(user_id,lock=True)
        with Session(migrated_engine) as notifier, notifier.begin():
            assert notifier.scalar(select(User.id).where(User.id==user_id)
                .with_for_update(read=True,key_share=True,nowait=True))==user_id
    with Session(migrated_engine) as cleanup, cleanup.begin():
        cleanup.delete(cleanup.get(User,user_id))
