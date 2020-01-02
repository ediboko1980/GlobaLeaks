# -*- coding: UTF-8
from globaleaks.db.migrations.update import MigrationBase as MigrationScript
from globaleaks.models import Model
from globaleaks.models.properties import *
from globaleaks.utils.utility import datetime_never, datetime_now, datetime_null


class InternalTip_v_42(Model):
    __tablename__ = 'internaltip'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4, nullable=False)

    tid = Column(Integer, default=1, nullable=False)

    encrypted = Column(Boolean, default=False, nullable=False)

    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    update_date = Column(DateTime, default=datetime_now, nullable=False)
    context_id = Column(UnicodeText(36), nullable=False)
    questionnaire_hash = Column(UnicodeText(64), nullable=False)
    preview = Column(JSON, nullable=False)
    progressive = Column(Integer, default=0, nullable=False)
    https = Column(Boolean, default=False, nullable=False)
    total_score = Column(Integer, default=0, nullable=False)
    expiration_date = Column(DateTime, nullable=False)
    identity_provided = Column(Boolean, default=False, nullable=False)
    identity_provided_date = Column(DateTime, default=datetime_null, nullable=False)
    enable_two_way_comments = Column(Boolean, default=True, nullable=False)
    enable_two_way_messages = Column(Boolean, default=True, nullable=False)
    enable_attachments = Column(Boolean, default=True, nullable=False)
    enable_whistleblower_identity = Column(Boolean, default=False, nullable=False)

    wb_last_access = Column(DateTime, default=datetime_now, nullable=False)
    wb_access_counter = Column(Integer, default=0, nullable=False)

    status = Column(UnicodeText(36), nullable=False)
    substatus = Column(UnicodeText(36), nullable=True)


class Signup_v_42(Model):
    __tablename__ = 'signup'

    id = Column(Integer, primary_key=True, nullable=False)
    tid = Column(Integer, nullable=False)
    subdomain = Column(UnicodeText, unique=True, nullable=False)
    language = Column(UnicodeText, nullable=False)
    name = Column(UnicodeText, nullable=False)
    surname = Column(UnicodeText, nullable=False)
    role = Column(UnicodeText, default='', nullable=False)
    phone = Column(UnicodeText, default='', nullable=False)
    email = Column(UnicodeText, nullable=False)
    use_case = Column(UnicodeText, default='', nullable=False)
    use_case_other = Column(UnicodeText, default='', nullable=False)
    organization_name = Column(UnicodeText, default='', nullable=False)
    organization_type = Column(UnicodeText, default='', nullable=False)
    organization_location1 = Column(UnicodeText, default='', nullable=False)
    organization_location2 = Column(UnicodeText, default='', nullable=False)
    organization_location3 = Column(UnicodeText, default='', nullable=False)
    organization_location4 = Column(UnicodeText, default='', nullable=False)
    organization_site = Column(UnicodeText, default='', nullable=False)
    organization_number_employees = Column(UnicodeText, default='', nullable=False)
    organization_number_users = Column(UnicodeText, default='', nullable=False)
    hear_channel = Column(UnicodeText, default='', nullable=False)
    activation_token = Column(UnicodeText, nullable=False)

    password_admin = Column(UnicodeText, default='', nullable=False)
    password_recipient = Column(UnicodeText, default='', nullable=False)

    client_ip_address = Column(UnicodeText, default='', nullable=False)
    client_user_agent = Column(UnicodeText, default='', nullable=False)
    registration_date = Column(DateTime, default=datetime_now, nullable=False)
    tos1 = Column(UnicodeText, default='', nullable=False)
    tos2 = Column(UnicodeText, default='', nullable=False)


class User_v_42(Model):
    __tablename__ = 'user'
    id = Column(UnicodeText(36), primary_key=True, default=uuid4, nullable=False)
    tid = Column(Integer, default=1, nullable=False)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    username = Column(UnicodeText, default='', nullable=False)
    password = Column(UnicodeText, default='', nullable=False)
    salt = Column(UnicodeText(24), nullable=False)
    name = Column(UnicodeText, default='', nullable=False)
    description = Column(JSON, default=dict, nullable=False)
    role = Column(UnicodeText, default='receiver', nullable=False)
    state = Column(UnicodeText, default='enabled', nullable=False)
    last_login = Column(DateTime, default=datetime_null, nullable=False)
    mail_address = Column(UnicodeText, default='', nullable=False)
    language = Column(UnicodeText, nullable=False)
    password_change_needed = Column(Boolean, default=True, nullable=False)
    password_change_date = Column(DateTime, default=datetime_null, nullable=False)
    auth_token = Column(UnicodeText, default='', nullable=False)
    enc_prv_key = Column(UnicodeText, default='', nullable=False)
    enc_pub_key = Column(UnicodeText, default='', nullable=False)
    can_edit_general_settings = Column(Boolean, default=False, nullable=False)
    change_email_address = Column(UnicodeText, default='', nullable=False)
    change_email_token = Column(UnicodeText, unique=True, nullable=True)
    change_email_date = Column(DateTime, default=datetime_never, nullable=False)
    reset_password_token = Column(UnicodeText, unique=True, nullable=True)
    reset_password_date = Column(UnicodeText, default=datetime_never, nullable=False)
    pgp_key_fingerprint = Column(UnicodeText, default='', nullable=False)
    pgp_key_public = Column(UnicodeText, default='', nullable=False)
    pgp_key_expiration = Column(DateTime, default=datetime_null, nullable=False)
