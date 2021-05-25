import argparse
from datetime import timezone
import psycopg2
import psycopg2.extras
import json
import datetime
from typing import Union
import pika
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater, CallbackQueryHandler

from lib.config import Config, MODE_CORE, MODE_BOT, MODE_WORKER, MODE_UPDATER
from lib.log import get_logger
from lib.platform import Platform
from lib.player import Player, STATUS_VALID
from lib.telegram import set_logger, echo, start, set_platforms, main_menu, account_choice, platform_choice, set_connect, telegram_init, game_navigation, game_choice, achievement_navigation, locale_choice, set_config as set_telegram_config, admin_choice, stats_choice, shutdown_choice
from lib.queue import get_mq_connect, MAIN_QUEUE_NAME, BOT_QUEUE_NAME, WORKER_QUEUE_NAME, UPDATER_QUEUE_NAME, set_config as set_queue_config, set_logger as set_queue_log, enqueue_command
from lib.queue_handlers import set_telegram, on_create, on_delete
from lib.platforms.steam import init_platform as init_steam
from lib.stats import get_stats


global load_log


def load(config: Config, load_games: bool = True, load_achievements: bool = True):
    global load_log
    platforms = [
        init_steam(config)]
    Platform.set_load_log(load_log)
    if load_games:
        for i in platforms:
            i.load_games(load_achievements)
    return platforms


def load_players(platform: Platform, config: Config, player_id: Union[int, None] = None):
    global load_log
    conn = psycopg2.connect(dbname=config.db_name, user=config.db_user,
                            password=config.db_password, host=config.db_host, port=config.db_port)
    cursor = conn.cursor()

    if player_id is None:
        cursor.execute("""
        select id, platform_id, name, ext_id, telegram_id, dt_update from achievements_hunt.players where platform_id = %s 
        and status_id = %s order by id
        """, (platform.id, STATUS_VALID))
    else:
        cursor.execute("""
            select id, platform_id, name, ext_id, telegram_id, dt_update from achievements_hunt.players where platform_id = %s
             and id = %s  order by id
            """, (platform.id, player_id))
    players = []
    for id, platform_id, name, ext_id, telegram_id, dt_updated in cursor:
        load_log.info("Loaded player {0} with id {1}, ext_id {2}, for platform {3} on platform".format(name, ext_id, id, platform.name))
        test = Player(name=name, platform=platform, ext_id=ext_id, id=id, telegram_id=telegram_id, dt_updated=dt_updated)
        players.append(test)
    conn.close()
    return players


def main_bot(config: Config):
    global load_log
    load_log = get_logger("loader_bot", config.log_level, True)
    queue_log = get_logger("Rabbit_bot", config.log_level, True)
    set_logger(config)
    set_queue_log(queue_log)
    telegram_init()
    Platform.set_config(config)
    set_connect(Platform.get_connect())
    set_telegram_config(config)
    platforms = load(config, True, False)
    set_platforms(platforms)

    set_queue_config(config)

    updater = Updater(token=config.secret, use_context=True)
    dispatcher = updater.dispatcher

    set_telegram(updater.dispatcher.bot)
    start_handler = CommandHandler('start', start)
    echo_handler = MessageHandler(Filters.text & (~Filters.command), echo)
    main_menu_handler = CallbackQueryHandler(main_menu, pattern="main_")
    account_choice_handler = CallbackQueryHandler(account_choice, pattern="accounts_")
    platform_menu_handler = CallbackQueryHandler(platform_choice, pattern="PLATFORM_")
    games_menu_handler = CallbackQueryHandler(game_choice, pattern="games_")
    games_navigation_handler = CallbackQueryHandler(game_navigation, pattern="list_of_games")
    achievement_navigation_handler = CallbackQueryHandler(achievement_navigation, pattern="list_of_achievements")
    language_handler = CallbackQueryHandler(locale_choice, pattern="LOCALE")
    admin_handler = CallbackQueryHandler(admin_choice, pattern="admin_")
    shutdown_handler = CallbackQueryHandler(shutdown_choice, pattern="shutdown_")
    stats_handler = CallbackQueryHandler(stats_choice, pattern="stats_")
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(echo_handler)
    dispatcher.add_handler(main_menu_handler)
    dispatcher.add_handler(platform_menu_handler)
    dispatcher.add_handler(account_choice_handler)
    dispatcher.add_handler(games_menu_handler)
    dispatcher.add_handler(games_navigation_handler)
    dispatcher.add_handler(achievement_navigation_handler)
    dispatcher.add_handler(language_handler)
    dispatcher.add_handler(admin_handler)
    dispatcher.add_handler(shutdown_handler)
    dispatcher.add_handler(stats_handler)

    updater.start_polling()

    for i in config.admin_list:
        updater.dispatcher.bot.send_message(chat_id=i,
                                            text="Bot started at {0}.".format(datetime.datetime.now()))
    m_queue = get_mq_connect(config)
    m_channel = m_queue.channel()
    m_channel.queue_declare(queue=BOT_QUEUE_NAME, durable=True)
    m_channel.exchange_declare(exchange='main',
                               exchange_type='direct')
    m_channel.queue_bind(exchange='main',
                         queue=BOT_QUEUE_NAME,
                         routing_key=config.mode)
    is_running = True

    while is_running:

        try:

            for method_frame, properties, body in m_channel.consume(BOT_QUEUE_NAME, inactivity_timeout=5,
                                                                    auto_ack=False,
                                                                    arguments={"routing_key": config.mode}):
                if body is not None:
                    queue_log.info("Received user message {0} with delivery_tag {1}".format(body,
                                                                                            method_frame.delivery_tag))
                    # cmd_response_callback(None, method_frame, properties, body)
                    cmd = json.loads(body)
                    cmd_type = cmd.get("cmd")
                    chat_id = cmd.get("chat_id")
                    if cmd_type == 'msg_to_user':
                        updater.dispatcher.bot.send_message(chat_id=chat_id, text=cmd.get("text"))
                    elif cmd_type == 'stop_server':
                        is_running = False
                        queue_log.info("Stop smd received")
                    elif cmd_type == "process_response":
                        for i in config.admin_list:
                            updater.dispatcher.bot.send_message(chat_id=i, text=cmd.get("text"))
                    m_channel.basic_ack(method_frame.delivery_tag)
                    queue_log.info("User message " + str(body) + " with delivery_tag " +
                                   str(method_frame.delivery_tag) + " acknowledged")
                else:
                    queue_log.info("No more messages in {0}".format(BOT_QUEUE_NAME))
                    m_channel.cancel()
                    break
        except BaseException as err:
            queue_log.critical(err)
            if config.supress_errors:
                pass
            else:
                raise
    updater.stop()
    queue_log.info("Job finished.")
    exit(0)


def main_core(config: Config):
    global load_log
    load_log = get_logger("loader_core", config.log_level, True)
    queue_log = get_logger("Rabbit_core", config.log_level, True)

    set_logger(config)
    set_queue_config(config)
    set_queue_log(queue_log)

    Platform.set_config(config)
    platforms = load(config, load_achievements=False, load_games=False)
    set_platforms(platforms)
    set_connect(Platform.get_connect())

    m_queue = get_mq_connect(config)
    m_channel = m_queue.channel()
    m_channel.queue_declare(queue=MAIN_QUEUE_NAME, durable=True)
    m_channel.exchange_declare(exchange='main',
                               exchange_type='direct')
    m_channel.queue_bind(exchange='main',
                         queue=MAIN_QUEUE_NAME,
                         routing_key=config.mode)

    is_running = True

    while is_running:

        try:
            for method_frame, properties, body in m_channel.consume(MAIN_QUEUE_NAME, inactivity_timeout=5,
                                                                    auto_ack=False,
                                                                    arguments={"routing_key": config.mode}):
                if body is not None:
                    queue_log.info("Received user message {0} with delivery_tag {1}".format(body,
                                                                                            method_frame.delivery_tag))
                    cmd = json.loads(body)
                    cmd_type = cmd.get("cmd")
                    platform_id = cmd.get("platform_id")
                    player_id = cmd.get("player_id")
                    if cmd_type == 'create_player':
                        for i in platforms:
                            if i.id == platform_id:
                                players = load_players(platform=i, config=config, player_id=player_id)
                                if len(players) > 0:
                                    player = players[0]
                                    on_create(platform=i, player=player)
                                    load_log.error("Player {0} validated".format(player_id))
                                else:
                                    load_log.error("Player {0} not found".format(player_id))
                    elif cmd_type == 'delete_user':
                        for i in platforms:
                            if i.id == platform_id:
                                players = load_players(platform=i, config=config, player_id=player_id)
                                if len(players) > 0:
                                    player = players[0]
                                    on_delete(platform=i, player=player)
                                    load_log.error("Player {0} deleted".format(player_id))
                                else:
                                    load_log.error("Player {0} not found".format(player_id))
                    elif cmd_type == 'stop_server':
                        is_running = False
                        cmd = {"cmd": "process_response", "text": "Core shutdown started"}
                        enqueue_command(cmd, MODE_BOT)
                    elif cmd_type == "get_stats":
                        msg = get_stats()
                        msg["module"] = "Core"
                        cmd = {"cmd": "process_response", "text": str(msg)}
                        enqueue_command(cmd, MODE_BOT)
                    else:
                        queue_log.info("Unknown command type {0}".format(cmd_type))
                    m_channel.basic_ack(method_frame.delivery_tag)
                    queue_log.info("User message " + str(body) + " with delivery_tag " +
                                   str(method_frame.delivery_tag) + " acknowledged")
                else:
                    queue_log.info("No more messages in {0}".format(MAIN_QUEUE_NAME))
                    m_channel.cancel()
                    break
        except BaseException as err:
            queue_log.critical(err)
            if config.supress_errors:
                pass
            else:
                raise


def main_updater(config: Config):
    global load_log
    load_log = get_logger("loader_updater", config.log_level, True)
    queue_log = get_logger("Rabbit_updater", config.log_level, True)

    set_logger(config)
    set_queue_config(config)
    set_queue_log(queue_log)

    Platform.set_config(config)
    platforms = load(config, load_games=False)
    connect = Platform.get_connect()

    m_queue = get_mq_connect(config)
    m_channel = m_queue.channel()
    m_channel.queue_declare(queue=UPDATER_QUEUE_NAME, durable=True)
    m_channel.exchange_declare(exchange='main',
                               exchange_type='direct')
    m_channel.queue_bind(exchange='main',
                         queue=UPDATER_QUEUE_NAME,
                         routing_key=config.mode)

    is_running = True

    while is_running:

        try:
            cursor = connect.cursor()
            # Process new games queue - recalc owner numbers and percent of achievers
            cursor.execute("""
            select id, game_id, operation from achievements_hunt.queue_games_update order by game_id for update skip locked fetch first 1000 rows only
            """)
            games = {}
            recs = []
            for id_rec, game_id, operation in cursor:
                if game_id not in games:
                    games[game_id] = 0
                if operation == "INSERT":
                    games[game_id] += 1
                else:
                    games[game_id] -= 1
                recs.append((id_rec, ))
            if len(games) > 0:
                cursor.execute("""
                        PREPARE upd_games as update achievements_hunt.games set num_owners = num_owners + $1 where id = $2 
                        """)
                game_res = []
                game_4_ach = []
                for i in games:
                    game_res.append((games[i], i))
                    game_4_ach.append((i, ))

                psycopg2.extras.execute_batch(cursor, """EXECUTE upd_games (%s, %s)""", game_res)
                cursor.execute("""
                PREPARE del_q as delete from achievements_hunt.queue_games_update where id = $1
                """)
                cursor.execute("""PREPARE upd_achievement as 
                                update achievements_hunt.achievements as a set percent_owners = case when num_owners > 0 then 
                                round(a.num_owners * 100 / 
                                greatest(1, (select g.num_owners from achievements_hunt.games as g where g.id = a.game_id
                                and g.platform_id = a.platform_id)), 2)
                                else 0
                                end
                                where a.game_id = $1
                                """)
                psycopg2.extras.execute_batch(cursor, """EXECUTE upd_achievement (%s)""", game_4_ach)
                psycopg2.extras.execute_batch(cursor, """EXECUTE del_q (%s)""", recs)
                cursor.execute("""DEALLOCATE  upd_games""")
                cursor.execute("""DEALLOCATE  del_q""")
                cursor.execute("""DEALLOCATE  upd_achievement""")
            connect.commit()

            # Process new achievements queue - reset perfect games and recalc % complete for all players
            cursor.execute("""
                                select id, game_id, platform_id from achievements_hunt.queue_achievements_update order by achievement_id for update skip locked fetch first 1000 rows only
                                """)
            recs = []
            games = []
            games_ids = []
            for id_rec, game_id, platform_id in cursor:
                if game_id not in games_ids:
                    games_ids.append(game_id)
                    games.append((game_id, platform_id))
                recs.append((id_rec,))
            if len(games) > 0:

                cursor.execute("""
                                                        PREPARE update_player_games as 
                                                        update achievements_hunt.player_games pg set percent_complete =
                                                        round(
                                                        (select count(1) from achievements_hunt.player_achievements a
                                                         where a.platform_id = pg.platform_id
                                                         and a.game_id = pg.game_id
                                                         and a.player_id = pg.player_id) * 100 /
                                                        (select count(1) from  achievements_hunt.achievements ac
                                                        where ac.platform_id = pg.platform_id
                                                        and ac.game_id = pg.game_id)  , 2)
                                                         where pg.game_id = $1
                                                         and pg.platform_id = $2
                                                        """)
                cursor.execute("""
                                                        PREPARE update_player_games_perf as 
                                                        update achievements_hunt.player_games pg 
                                                        set is_perfect = (percent_complete = 100)
                                                        where pg.game_id = $1 and pg.platform_id = $2
                                                        """)
                psycopg2.extras.execute_batch(cursor, """EXECUTE update_player_games  (%s, %s)""", games)
                psycopg2.extras.execute_batch(cursor, """EXECUTE update_player_games_perf  (%s, %s)""", games)

                cursor.execute("""
                                            PREPARE del_q as delete from achievements_hunt.queue_achievements_update where id = $1
                                            """)
                psycopg2.extras.execute_batch(cursor, """EXECUTE del_q (%s)""", recs)

                cursor.execute("""DEALLOCATE  update_player_games""")
                cursor.execute("""DEALLOCATE  update_player_games_perf""")
                cursor.execute("""DEALLOCATE  del_q""")
            connect.commit()

            # Process player achievements queue, renew percent of achievers and update player perfect games status
            cursor.execute("""
                    select id, achievement_id, player_id, game_id, platform_id, operation from achievements_hunt.queue_player_achievements_update order by achievement_id for update skip locked fetch first 1000 rows only
                    """)
            achievements = {}
            recs = []
            player_games = []
            for id_rec, achievement_id, player_id, game_id, platform_id, operation in cursor:
                if achievement_id not in achievements:
                    achievements[achievement_id] = 0
                if operation == "INSERT":
                    achievements[achievement_id] += 1
                else:
                    achievements[achievement_id] -= 1
                recs.append((id_rec,))
                player_games.append((player_id, game_id, platform_id))
            if len(player_games) > 0:
                cursor.execute("""
                                PREPARE upd_achievements as update achievements_hunt.achievements set num_owners = num_owners + $1 where id = $2 
                                """)
                game_res = []
                game_4_ach = []
                for i in achievements:
                    game_res.append((achievements[i], i))
                    game_4_ach.append((i,))

                psycopg2.extras.execute_batch(cursor, """EXECUTE upd_achievements (%s, %s)""", game_res)

                cursor.execute("""PREPARE upd_achievement_percent as 
                                        update achievements_hunt.achievements as a set percent_owners = case when num_owners > 0 then 
                                        round(a.num_owners * 100 / 
                                        greatest((select g.num_owners from achievements_hunt.games as g where g.id = a.game_id
                                        and g.platform_id = a.platform_id), 1), 2)
                                        else 0
                                        end
                                        where a.id = $1
                                        """)
                psycopg2.extras.execute_batch(cursor, """EXECUTE upd_achievement_percent (%s)""", game_4_ach)
                cursor.execute("""
                                            PREPARE update_player_games as 
                                            update achievements_hunt.player_games pg set percent_complete =
                                            round(
                                            (select count(1) from achievements_hunt.player_achievements a
                                             where a.platform_id = pg.platform_id
                                             and a.game_id = pg.game_id
                                             and a.player_id = pg.player_id) * 100 /
                                            (select count(1) from achievements_hunt.achievements ac
                                            where ac.platform_id = pg.platform_id
                                            and ac.game_id = pg.game_id), 2) 
                                             where pg.player_id = $1 and pg.game_id = $2
                                             and pg.platform_id = $3 
                                            """)
                cursor.execute("""
                                            PREPARE update_player_games_perf as 
                                            update achievements_hunt.player_games pg 
                                            set is_perfect = (percent_complete = 100)
                                            where pg.player_id = $1 and pg.game_id = $2 and pg.platform_id = $3
                                            """)
                psycopg2.extras.execute_batch(cursor, """EXECUTE update_player_games (%s, %s, %s)""", player_games)
                psycopg2.extras.execute_batch(cursor, """EXECUTE update_player_games_perf (%s, %s, %s)""", player_games)

                cursor.execute("""
                                PREPARE del_q as delete from achievements_hunt.queue_player_achievements_update where id = $1
                                """)
                psycopg2.extras.execute_batch(cursor, """EXECUTE del_q (%s)""", recs)
                cursor.execute("""DEALLOCATE  update_player_games""")
                cursor.execute("""DEALLOCATE  update_player_games_perf""")
                cursor.execute("""DEALLOCATE  upd_achievements""")
                cursor.execute("""DEALLOCATE  del_q""")
                cursor.execute("""DEALLOCATE  upd_achievement_percent""")
            connect.commit()

            for method_frame, properties, body in m_channel.consume(UPDATER_QUEUE_NAME, inactivity_timeout=5,
                                                                    auto_ack=False,
                                                                    arguments={"routing_key": config.mode}):
                if body is not None:
                    queue_log.info("Received user message {0} with delivery_tag {1}".format(body,
                                                                                            method_frame.delivery_tag))
                    cmd = json.loads(body)
                    cmd_type = cmd.get("cmd")
                    if cmd_type == 'stop_server':
                        is_running = False
                        cmd = {"cmd": "process_response", "text": "Updater shutdown started"}
                        enqueue_command(cmd, MODE_BOT)
                    elif cmd_type == "get_stats":
                        msg = get_stats()
                        msg["module"] = "Updater"
                        cmd = {"cmd": "process_response", "text": str(msg)}
                        enqueue_command(cmd, MODE_BOT)
                    m_channel.basic_ack(method_frame.delivery_tag)
                    queue_log.info("User message " + str(body) + " with delivery_tag " +
                                   str(method_frame.delivery_tag) + " acknowledged")
                else:
                    queue_log.info("No more messages in {0}".format(UPDATER_QUEUE_NAME))
                    m_channel.cancel()
                    break
        except BaseException as err:
            queue_log.critical(err)
            if config.supress_errors:
                pass
            else:
                raise


def main_worker(config: Config):
    global load_log
    load_log = get_logger("loader_worker", config.log_level, True)
    queue_log = get_logger("Rabbit_worker", config.log_level, True)
    renew_log = get_logger("renew_worker", config.log_level, True)

    set_logger(config)
    set_queue_config(config)
    set_queue_log(queue_log)

    Platform.set_config(config)
    platforms = load(config)
    set_platforms(platforms)
    set_connect(Platform.get_connect())

    m_queue = get_mq_connect(config)
    m_channel = m_queue.channel()

    m_channel.queue_declare(queue=WORKER_QUEUE_NAME, durable=True)

    m_channel.exchange_declare(exchange='main',
                               exchange_type='direct')
    m_channel.queue_bind(exchange='main',
                         queue=WORKER_QUEUE_NAME,
                         routing_key=config.mode)

    is_running = True

    dt_next_update = []
    conn = Platform.get_connect()
    cursor = conn.cursor()
    for i in platforms:
        cursor.execute("""
        select max(dt_next_update) from achievements_hunt.update_history where id_platform = %s and dt_ended is not null
        """, (i.id, ))
        ret = cursor.fetchone()
        if ret is not None and ret[0] is not None:
            dt_next_update.append(ret[0])
        else:
            dt_next_update.append(datetime.datetime.now())
        i.reset_games()
        i.load_languages()
        i.set_next_language()

    cur_players = []
    platform_players = []

    while is_running:

        try:

            for i in range(len(platforms)):
                if datetime.datetime.now().replace(tzinfo=timezone.utc) > dt_next_update[i].replace(tzinfo=timezone.utc):
                    renew_log.info("Update platform {0}, next update {1}".format(platforms[i].name, dt_next_update[i]))
                    platforms[i].set_next_language()
                    cursor.execute("""
                    select count(1) from achievements_hunt.update_history where id_platform = %s 
                    and dt_ended is null
                    """, (platforms[i].id,))
                    cnt, = cursor.fetchone()
                    if cnt == 0:
                        cursor.execute("""
                                        insert into achievements_hunt.update_history(id_platform) 
                                        values (%s)
                                        """, (platforms[i].id,))
                        conn.commit()
                    if len(platform_players) == 0:
                        renew_log.info("Update loading players for platform {0}".format(platforms[i].name))
                        platform_players.append(load_players(platforms[i], config))
                        cur_players.append(0)
                    else:
                        renew_log.info(
                            "Update platform {0} resumed from position {1}".format(platforms[i].name, cur_players[i]))
                    start_pos = 0
                    for j in range(cur_players[i], len(platform_players[i])):
                        cur_players[i] = j
                        renew_log.info("Update platform {0} for player {1}/{2}".format(platforms[i].name,
                                                                                       platform_players[i][j].ext_id,
                                                                                       len(platform_players[i])))
                        platform_players[i][j].renew()
                        platform_players[i][j].save()
                        start_pos += 1
                        if start_pos >= 100:
                            renew_log.info(
                                "Update platform {0} paused in position {1}".format(platforms[i].name, cur_players[i]))
                            break
                    platforms[i].save()
                    if cur_players[i] + 1 >= len(platform_players[i]):
                        dt_next_update[i] = datetime.datetime.now() + \
                                            datetime.timedelta(seconds=platforms[i].config.update_interval)
                        platform_players[i] = []
                        platforms[i].mark_language_done()
                        renew_log.info("Update platform {0} finished, next_update {1}".format(platforms[i].name,
                                                                                              dt_next_update[i]))
                        cursor.execute("""
                                update achievements_hunt.update_history 
                                    set dt_ended = current_timestamp, 
                                    dt_next_update = %s
                                    where id_platform = %s
                                    and dt_ended is null
                                """, (dt_next_update[i], platforms[i].id ))
                        conn.commit()
                    else:
                        renew_log.info(
                            "Update platform {0} postponed, progress {1}/{2}".format(platforms[i].name, cur_players[i],
                                                                                     len(platform_players[i])))
        except BaseException as err:
            queue_log.critical(err)
            if config.supress_errors:
                pass
            else:
                raise

        try:

            m_queue = get_mq_connect(config)
            m_channel = m_queue.channel()

            for method_frame, properties, body in m_channel.consume(WORKER_QUEUE_NAME, inactivity_timeout=5,
                                                                    auto_ack=False):
                if body is not None:
                    queue_log.info("Received user message {0} with delivery_tag {1}".format(body,
                                                                                            method_frame.delivery_tag))
                    # cmd_response_callback(None, method_frame, properties, body)
                    cmd = json.loads(body)
                    cmd_type = cmd.get("cmd")
                    if cmd_type == 'renew_achievements':
                        platform_id = cmd.get("platform_id")
                        player_id = cmd.get("player_id")
                        dt_sent = cmd.get("dt_sent")
                        dt_sent = datetime.datetime.fromtimestamp(dt_sent)
                        queue_log.info("Start renew achievements for player {2} and platform {3} becauese msg {0} "
                                       "with delivery_tag {1}".format(body, method_frame.delivery_tag,
                                                                      player_id, platform_id))
                        player = None
                        for i in platforms:
                            queue_log.debug("Check platform {0} {1}".format(i.name, i.id))
                            if int(i.id) == int(platform_id):
                                players = load_players(platform=i, config=config, player_id=player_id)
                                if len(players) > 0:
                                    player = players[0]
                                    if player.dt_updated is None or player.dt_updated.replace(tzinfo=timezone.utc) < dt_sent.replace(tzinfo=timezone.utc):
                                        queue_log.info(
                                            "Start actially renew achievements for player {2}  and platform {3} becauese msg {0} with delivery_tag {1}".format(
                                                body,
                                                method_frame.delivery_tag,
                                                player_id, i.name))
                                        i.set_def_locale()
                                        player.renew()
                                        player.platform.save()
                                        player.save()
                                        cmd = {"chat_id": player.telegram_id, "cmd": "msg_to_user",
                                                           "text": 'Achievements for account {} platform {} renewed'.format(player.ext_id, i.name)}
                                        enqueue_command(cmd, MODE_BOT)
                                    else:
                                        queue_log.info(
                                            "Skipped  renew achievements for player {2} and platform {3} becauese msg {0} with delivery_tag {1} was sent at {4} and last renew was {5}".format(
                                                body,
                                                method_frame.delivery_tag,
                                                player_id, i.name, dt_sent, player.dt_updated))
                                else:
                                    queue_log.error(
                                        "Player {0} for platform {1} wasn't found in db".format(player_id, platform_id))
                                pass
                        if player is None:
                            queue_log.error("Player {0} for platform {1} wasn't proceed".format(player_id, platform_id))

                    elif cmd_type == 'stop_server':
                        is_running = False
                        cmd = {"cmd": "process_response", "text": "Worker shutdown started"}
                        enqueue_command(cmd, MODE_WORKER)
                    elif cmd_type == "get_stats":
                        msg = get_stats()
                        # TODO less expensive way
                        cursor.execute("""
                                select count(1) from achievements_hunt.players
                                """)
                        res = cursor.fetchone()
                        msg["players"] = res[0]
                        msg["module"] = "Worker"
                        cmd = {"cmd": "process_response", "text": str(msg)}
                        enqueue_command(cmd, MODE_BOT)
                    try:
                        m_channel.basic_ack(method_frame.delivery_tag)
                    except BaseException as exc:
                        queue_log.info("User message " + str(body) + " with delivery_tag " +
                                       str(method_frame.delivery_tag) + " acknowledged with error, resending")
                        # TODO: handle
                        raise

                    queue_log.info("User message " + str(body) + " with delivery_tag " +
                                   str(method_frame.delivery_tag) + " acknowledged")
                else:
                    queue_log.info("No more messages in {0}".format(WORKER_QUEUE_NAME))
                    m_channel.cancel()
                    break
        except pika.exceptions.AMQPError as exc:
            queue_log.critical(exc)
            m_queue = get_mq_connect(config)
            m_channel = m_queue.channel()
        except BaseException as err:
            queue_log.critical(err)
            if config.supress_errors:
                pass
            else:
                raise


def main():
    parser = argparse.ArgumentParser(description='Idle RPG server.')
    parser.add_argument("--config", '-cfg', help="Path to config file", action="store", default="cfg//main.json")
    parser.add_argument("--mode", '-m', help="mode", action="store", default="core")
    args = parser.parse_args()

    mode = args.mode
    config = Config(args.config, mode=mode)

    if mode not in [MODE_CORE, MODE_BOT, MODE_WORKER, MODE_UPDATER]:
        raise ValueError("Mode {0} not supported".format(mode))
    if mode == MODE_BOT:
        main_bot(config)
    elif mode == MODE_CORE:
        main_core(config)
    elif mode == MODE_WORKER:
        main_worker(config)
    elif mode == MODE_UPDATER:
        main_updater(config)


if __name__ == '__main__':
    main()
