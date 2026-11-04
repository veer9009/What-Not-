"""Operator-run bounded commands; no scheduler or network listener."""
import argparse
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.db.session import build_engine
from app.services.orders import OrderService
from app.services.workers import process_email


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['auto-complete', 'process-email', 'expire-properties'])
    args = parser.parse_args()
    settings = Settings()
    engine = build_engine(settings)
    try:
        if args.command == 'process-email':
            count = process_email(engine, settings)
        else:
            with Session(engine) as session, session.begin():
                if args.command == 'expire-properties':
                    from app.services.properties import PropertyService
                    count = PropertyService(session).expire_due(settings.outbox_batch_size)
                else:
                    count = OrderService(session, settings=settings).auto_complete_due()
        print(f'{args.command}: processed={count}')
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
