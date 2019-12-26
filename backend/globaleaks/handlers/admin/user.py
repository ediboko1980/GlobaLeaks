# -*- coding: utf-8
#
#   user
#   *****
# Implementation of the User model functionalities
#
from globaleaks import models
from globaleaks.db import db_refresh_memory_variables
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.user import db_get_user, \
                                     parse_pgp_options, \
                                     user_serialize_user

from globaleaks.models import fill_localized_keys
from globaleaks.orm import transact
from globaleaks.rest import requests, errors
from globaleaks.state import State
from globaleaks.utils.crypto import GCE
from globaleaks.utils.utility import datetime_now, uuid4


@transact
def create_user(session, tid, request, language):
    return user_serialize_user(session, db_create_user(session, tid, request, language), language)


def db_create_user(session, tid, request, language):
    request['tid'] = tid

    fill_localized_keys(request, models.User.localized_keys, language)

    if request['username']:
        user = session.query(models.User).filter(models.User.username == request['username'],
                                                 models.User.tid == tid).one_or_none()
        if user is not None:
            raise errors.InputValidationError('Username already in use')

    user = models.User({
        'tid': tid,
        'username': request['username'],
        'role': request['role'],
        'state': 'enabled',
        'name': request['name'],
        'description': request['description'],
        'public_name': request['public_name'] if request['public_name'] else request['name'],
        'language': language,
        'password_change_needed': request['password_change_needed'],
        'mail_address': request['mail_address'],
        'can_edit_general_settings': request['can_edit_general_settings']
    })

    if not request['username']:
        user.username = user.id = uuid4()

    password = 'password'
    if request['password']:
        password = request['password']

    user.salt = GCE.generate_salt()
    user.password = GCE.hash_password(password, user.salt)

    # The various options related in manage PGP keys are used here.
    parse_pgp_options(user, request)

    session.add(user)

    session.flush()

    return user


def db_admin_update_user(session, tid, user_id, request, language):
    """
    Updates the specified user.
    """
    fill_localized_keys(request, models.User.localized_keys, language)

    user = db_get_user(session, tid, user_id)

    if user.username != request['username']:
        check = session.query(models.User).filter(models.User.username == request['username'],
                                                  models.User.tid == tid).one_or_none()
        if check is not None:
            raise errors.InputValidationError('Username already in use')

    user.update(request)

    password = request['password']
    if password and not user.crypto_pub_key:
        user.hash_alg = 'ARGON2'
        user.salt = GCE.generate_salt()
        user.password = GCE.hash_password(password, user.salt)
        user.password_change_date = datetime_now()

    # The various options related in manage PGP keys are used here.
    parse_pgp_options(user, request)

    if user.role == 'admin':
        db_refresh_memory_variables(session, [tid])

    return user


@transact
def admin_update_user(session, tid, user_id, request, language):
    return user_serialize_user(session, db_admin_update_user(session, tid, user_id, request, language), language)


@transact
def delete_user(session, tid, user_id):
    user = db_get_user(session, tid, user_id)

    if user is not None:
        session.delete(user)


def db_get_admin_users(session, tid):
    users = session.query(models.User).filter(models.User.role == 'admin',
                                              models.User.tid == tid)

    return [user_serialize_user(session, user, State.tenant_cache[tid].default_language) for user in users]


@transact
def get_receiver_list(session, tid, language):
    """
    Returns:
        (list) the list of recipients
    """
    users = session.query(models.User).filter(models.User.role == 'receiver',
                                              models.User.tid == tid)

    return [user_serialize_user(session, user, language) for user in users]


@transact
def get_user_list(session, tid, language):
    """
    Returns:
        (list) the list of users
    """
    users = session.query(models.User).filter(models.User.tid == tid)

    return [user_serialize_user(session, user, language) for user in users]


class UsersCollection(BaseHandler):
    check_roles = 'admin'
    cache_resource = True
    invalidate_cache = True

    def get(self):
        """
        Return all the users.
        """
        return get_user_list(self.request.tid, self.request.language)

    def post(self):
        """
        Create a new user
        """
        request = self.validate_message(self.request.content.read(),
                                        requests.UserUserDesc)

        return create_user(self.request.tid, request, self.request.language)


class UserInstance(BaseHandler):
    check_roles = 'admin'
    invalidate_cache = True

    def put(self, user_id):
        """
        Update the specified user.
        """
        request = self.validate_message(self.request.content.read(), requests.UserUserDesc)

        return admin_update_user(self.request.tid, user_id, request, self.request.language)

    def delete(self, user_id):
        """
        Delete the specified user.
        """
        return delete_user(self.request.tid, user_id)
