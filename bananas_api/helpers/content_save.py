import asyncio
import click
import logging

from collections import defaultdict

from .click import (
    click_additional_options,
    import_module,
)

from ..helpers.content_storage import get_indexed_package
from ..index.local import click_index_local
from ..index.github import click_index_github

log = logging.getLogger(__name__)

TIMER_TIMEOUT = 60 * 5

_pending_changes = defaultdict(set)
_timer = defaultdict(lambda: None)
_index_instance = None


def _store_on_disk_safe(package, display_name):
    try:
        _index_instance.store_package(package, display_name)
    except Exception:
        log.exception("Error while storing data to disk")


def store_on_disk(user, package=None):
    if package:
        _store_on_disk_safe(package, user.display_name)

    while _pending_changes[user.full_id]:
        content_type, unique_id = _pending_changes[user.full_id].pop()
        package = get_indexed_package(content_type, unique_id)

        _store_on_disk_safe(package, user.display_name)

    _index_instance.push_changes()


async def _timer_handler(user):
    await asyncio.sleep(TIMER_TIMEOUT)

    _timer[user.full_id] = None
    store_on_disk(user)


def queue_store_on_disk(user, package):
    _pending_changes[user.full_id].add((package["content_type"], package["unique_id"]))

    # Per user, start a timer. If it expires, we push the update. This
    # allows a user to take a bit of time to get its edits right, before we
    # make a commit out of it.
    if _timer[user.full_id]:
        _timer[user.full_id].cancel()

    loop = asyncio.get_event_loop()
    _timer[user.full_id] = loop.create_task(_timer_handler(user))


@click_additional_options
@click.option(
    "--index",
    help="Index backend to use.",
    type=click.Choice(["local", "github"], case_sensitive=False),
    required=True,
    callback=import_module("bananas_api.index", "Index"),
)
@click_index_local
@click_index_github
@click.option(
    "--commit-graceperiod",
    help="Graceperiod between commits to disk.",
    default=60 * 5,
    show_default=True,
    metavar="SECONDS",
)
def click_content_save(index, commit_graceperiod):
    global TIMER_TIMEOUT, _index_instance

    TIMER_TIMEOUT = commit_graceperiod
    _index_instance = index()

    _index_instance.load_all()


def reload_index():
    _index_instance.reload()
