import logging
from flask_babel import gettext
from flask import render_template

from aleph.core import db, settings, cache, celery
from aleph.authz import Authz
from aleph.mail import email_role
from aleph.model import Role, Subscription, Notification
from aleph.logic.notifications import channel

log = logging.getLogger(__name__)


def get_role(role_id):
    if role_id is None:
        return
    key = cache.object_key(Role, role_id)
    data = cache.get_complex(key)
    if data is None:
        log.debug("Role [%s]: object cache miss", role_id)
        role = Role.by_id(role_id)
        if role is None:
            return
        data = role.to_dict()
        cache.set_complex(key, data, expire=cache.EXPIRE)
    return data


def challenge_role(data):
    """Given an email address, this will send out a message to allow
    the user to then register an account."""
    signature = Role.SIGNATURE.dumps(data['email'])
    url = '{}activate/{}'.format(settings.APP_UI_URL, signature)
    role = Role(email=data['email'], name=data['email'])
    params = dict(url=url,
                  role=role,
                  ui_url=settings.APP_UI_URL,
                  app_title=settings.APP_TITLE)
    plain = render_template('email/registration_code.txt', **params)
    html = render_template('email/registration_code.html', **params)
    log.info("Challenge: %s", plain)
    email_role(role, gettext('Registration'), html=html, plain=plain)


def create_system_roles():
    log.info("Creating system roles...")
    Role.load_or_create(Role.SYSTEM_GUEST, Role.SYSTEM, 'All visitors')
    Role.load_or_create(Role.SYSTEM_USER, Role.SYSTEM, 'Logged-in users')
    db.session.commit()


def update_role(role):
    """Synchronize denormalised role configuration."""
    update_subscriptions.delay(role.id)
    refresh_role(role)


def refresh_role(role, sync=False):
    cache.kv.delete(cache.key(Authz.PREFIX, Authz.READ, role.id),
                    cache.key(Authz.PREFIX, Authz.WRITE, role.id),
                    cache.object_key(Role, role.id))


@celery.task(priority=3)
def update_subscriptions(role_id):
    role = Role.by_id(role_id, deleted=True)
    if role is None:
        return
    Subscription.unsubscribe(role=role, channel=channel(role))
    for group in Role.all_groups():
        Subscription.unsubscribe(role=role, channel=channel(group))

    if role.deleted_at is None and role.type == Role.USER:
        Subscription.subscribe(role, channel(role))
        Subscription.subscribe(role, Notification.GLOBAL)
        for group in role.roles:
            Subscription.subscribe(role, channel(group))
    db.session.commit()


def update_roles():
    q = db.session.query(Role)
    for role in q:
        refresh_role(role)
        update_role(role)


def check_visible(role, authz):
    """Users should not see group roles which they are not a part of."""
    if role is None:
        return False
    if authz.is_admin or role.id in authz.roles:
        return True
    return role.type == Role.USER


def check_editable(role, authz):
    """Check if a role can be edited by the current user."""
    if authz.is_admin:
        return True
    return role.id == authz.id
