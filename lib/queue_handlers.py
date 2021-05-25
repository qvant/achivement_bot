import gettext
from .player import Player
from .platform import Platform
from .queue import enqueue_command
from .config import MODE_BOT, MODE_WORKER

_ = gettext.gettext


def set_telegram(tlg):
    global bot
    bot = tlg


def on_create(player: Player, platform: Platform):
    global bot
    buf = platform.get_player_id(player.name)
    if buf is not None:
        player.set_ext_id(buf)
        buf = platform.validate_player(player.ext_id)
    if buf is not None:
        player.set_name(buf)
        player.mark_valid()
        player.save()
        resp = {"chat_id": player.telegram_id, "cmd": "msg_to_user",
                                               "text": _('Validation for account {} platform {} ok').format(player.ext_id, platform.name)}
        cmd = {"player_id": player.id, "cmd": "renew_achievements", "platform_id": player.platform.id}
        # player.renew()
        # player.save()
        enqueue_command(cmd, MODE_WORKER)
    else:
        player.delete()
        resp = {"chat_id": player.telegram_id, "cmd": "msg_to_user",
                "text": _('Validation for account {} platform {} failed').format(player.ext_id, platform.name)}
    enqueue_command(resp, MODE_BOT)


def on_delete(player: Player, platform: Platform):
    player.delete()
    resp = {"chat_id": player.telegram_id, "cmd": "msg_to_user",
            "text": _('Account {} for platform {} deleted').format(player.ext_id, platform.name)}
    enqueue_command(resp, MODE_BOT)
