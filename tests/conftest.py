import pytest
from app import create_app
from app.extensions import db
from app.models.user import User, Role
from app.models.bank_account import DemoBankAccount, UPIProfile, BankNames


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def test_user(app):
    with app.app_context():
        user = User(
            full_name="Tester One",
            email="tester@jaganpay.com",
            phone="+919000000001",
            role=Role.USER,
            is_verified=True,
            is_active=True,
        )
        user.set_password("TestPass123!")
        user.set_pin("1234")
        db.session.add(user)
        db.session.flush()

        upi = UPIProfile(user_id=user.id, upi_id="tester@jaganpay")
        db.session.add(upi)

        acc = DemoBankAccount(
            user_id=user.id,
            bank_name=BankNames.JAGAN_BANK,
            account_holder="Tester One",
            account_number_masked="•••• •••• 0001",
            demo_balance=25000.0,
            is_primary=True,
        )
        db.session.add(acc)
        db.session.commit()
        return user.id


@pytest.fixture
def test_receiver(app):
    with app.app_context():
        user = User(
            full_name="Receiver Demo",
            email="receiver@jaganpay.com",
            phone="+919000000002",
            role=Role.USER,
            is_verified=True,
            is_active=True,
        )
        user.set_password("TestPass123!")
        user.set_pin("1234")
        db.session.add(user)
        db.session.flush()

        upi = UPIProfile(user_id=user.id, upi_id="receiver@jaganpay")
        db.session.add(upi)

        acc = DemoBankAccount(
            user_id=user.id,
            bank_name=BankNames.ASTRA_BANK,
            account_holder="Receiver Demo",
            account_number_masked="•••• •••• 0002",
            demo_balance=10000.0,
            is_primary=True,
        )
        db.session.add(acc)
        db.session.commit()
        return user.id


@pytest.fixture
def test_admin(app):
    with app.app_context():
        admin = User(
            full_name="Admin Boss",
            email="admin@jaganpay.com",
            phone="+919000000099",
            role=Role.ADMIN,
            is_verified=True,
            is_active=True,
        )
        admin.set_password("AdminPass123!")
        admin.set_pin("1234")
        db.session.add(admin)
        db.session.flush()

        upi = UPIProfile(user_id=admin.id, upi_id="admin@jaganpay")
        db.session.add(upi)

        acc = DemoBankAccount(
            user_id=admin.id,
            bank_name=BankNames.JAGAN_BANK,
            account_holder="Admin Boss",
            account_number_masked="•••• •••• 9999",
            demo_balance=100000.0,
            is_primary=True,
        )
        db.session.add(acc)
        db.session.commit()
        return admin.id
