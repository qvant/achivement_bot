import codecs
import datetime
import json

from .security import is_password_encrypted, encrypt_password, decrypt_password
from .log import get_logger
from .stats import set_startup

LOG_CONFIG = "config"
CONFIG_PARAM_LOG_LEVEL = "LOG_LEVEL"
CONFIG_PARAM_QUEUE_PASSWORD = "QUEUE_PASSWORD"
CONFIG_PARAM_QUEUE_USER = "QUEUE_USER"
CONFIG_PARAM_QUEUE_HOST = "QUEUE_HOST"
CONFIG_PARAM_QUEUE_PORT = "QUEUE_PORT"
CONFIG_PARAM_DB_PORT = "DB_PORT"
CONFIG_PARAM_DB_NAME = "DB_NAME"
CONFIG_PARAM_DB_HOST = "DB_HOST"
CONFIG_PARAM_DB_USER = "DB_USER"
CONFIG_PARAM_DB_PASSWORD = "DB_PASSWORD"
CONFIG_PARAM_DB_UPDATE_SIZE = "DB_UPDATE_SIZE"
CONFIG_PARAM_DB_UPDATE_CYCLES = "DB_UPDATE_CYCLES"
CONFIG_PARAM_NEW_PATH = "CONFIG_PATH"
CONFIG_PARAM_CONFIG_RELOAD_TIME = "CONFIG_RELOAD_TIME"
CONFIG_PARAM_SERVER_NAME = "SERVER_NAME"
CONFIG_PARAM_UPDATE_INTERVAL = "UPDATE_INTERVAL"
CONFIG_PARAM_HALT_ON_ERRORS = "HALT_ON_ERRORS"
CONFIG_PARAM_BOT_SECRET = "BOT_SECRET"
CONFIG_PARAM_ADMIN_LIST = "ADMIN_ACCOUNTS"

MODE_CORE = "core"
MODE_BOT = "bot"
MODE_WORKER = "worker"
MODE_UPDATER = "updater"
MODE_GAME_UPDATER = "game_updater"

ALLOWED_MODES = [MODE_CORE, MODE_BOT, MODE_WORKER, MODE_GAME_UPDATER, MODE_UPDATER]


class Config:
    def __init__(self, file: str, reload: bool = False, mode=None):
        f = file
        fp = codecs.open(f, 'r', "utf-8")
        config = json.load(fp)
        if not reload:
            self.logger = get_logger(LOG_CONFIG, is_system=True)
            set_startup()
        if mode is not None:
            self.mode = mode
        self.logger.info("Read settings from {0}".format(file))
        self.file_path = file
        self.old_file_path = file
        self.log_level = config.get(CONFIG_PARAM_LOG_LEVEL)
        self.logger.setLevel(self.log_level)
        self.server_name = config.get(CONFIG_PARAM_SERVER_NAME)
        self.supress_errors = False
        self.update_interval = int(config.get(CONFIG_PARAM_UPDATE_INTERVAL))
        if not config.get(CONFIG_PARAM_HALT_ON_ERRORS):
            self.supress_errors = True
        self.secret = config.get(CONFIG_PARAM_BOT_SECRET)
        self.db_name = config.get(CONFIG_PARAM_DB_NAME)
        self.db_port = config.get(CONFIG_PARAM_DB_PORT)
        self.db_host = config.get(CONFIG_PARAM_DB_HOST)
        self.db_user = config.get(CONFIG_PARAM_DB_USER)
        self.db_password_read = config.get(CONFIG_PARAM_DB_PASSWORD)
        self.db_update_size = int(config.get(CONFIG_PARAM_DB_UPDATE_SIZE))
        self.db_update_cycles = int(config.get(CONFIG_PARAM_DB_UPDATE_CYCLES))
        if config.get(CONFIG_PARAM_NEW_PATH) is not None:
            self.file_path = config.get(CONFIG_PARAM_NEW_PATH)
        self.reload_time = config.get(CONFIG_PARAM_CONFIG_RELOAD_TIME)
        self.next_reload = datetime.datetime.now()
        self.reloaded = False
        self.db_credential_changed = False

        if is_password_encrypted(self.db_password_read):
            self.logger.info("DB password encrypted, do nothing")
            self.db_password = decrypt_password(self.db_password_read, self.server_name, self.db_port)
        elif self.mode == MODE_CORE:
            self.logger.info("DB password in plain text, start encrypt")
            password = encrypt_password(self.db_password_read, self.server_name, self.db_port)
            self._save_db_password(password)
            self.logger.info("DB password encrypted and save back in config")
            self.db_password = self.db_password_read
        else:
            self.logger.info("DB password in plain text, but work in not core")

        if is_password_encrypted(self.secret):
            self.logger.info("Secret in cypher text, start decryption")
            self.secret = decrypt_password(self.secret, self.server_name, self.db_port)
            self.logger.info("Secret was decrypted")
        elif self.mode == MODE_CORE:
            self.logger.info("Secret in plain text, start encryption")
            new_password = encrypt_password(self.secret, self.server_name, self.db_port)
            self._save_secret(new_password)
            self.logger.info("Secret was encrypted and saved")
        else:
            self.logger.info("Secret in plain text, but work in not core")

        self.admin_list = config.get(CONFIG_PARAM_ADMIN_LIST)

        self.queue_port = config.get(CONFIG_PARAM_QUEUE_PORT)
        self.queue_host = config.get(CONFIG_PARAM_QUEUE_HOST)
        self.queue_user = config.get(CONFIG_PARAM_QUEUE_USER)
        self.queue_password = config.get(CONFIG_PARAM_QUEUE_PASSWORD)

        if is_password_encrypted(self.queue_password):
            self.logger.info("Password in cypher text, start decryption")
            self.queue_password = decrypt_password(self.queue_password, self.server_name, self.queue_port)
            self.logger.info("Password was decrypted")
        elif self.mode == MODE_CORE:
            self.logger.info("Password in plain text, start encryption")
            new_password = encrypt_password(self.queue_password, self.server_name, self.queue_port)
            self._save_password(new_password)
            self.logger.info("Password was encrypted and saved")
        else:
            self.logger.info("Queue password in plain text, but work in not core")

    def _save_db_password(self, password: str):
        fp = codecs.open(self.file_path, 'r', "utf-8")
        config = json.load(fp)
        fp.close()
        fp = codecs.open(self.file_path, 'w', "utf-8")
        config[CONFIG_PARAM_DB_PASSWORD] = password
        json.dump(config, fp, indent=2)
        fp.close()

    def _save_password(self, password: str):
        fp = codecs.open(self.file_path, 'r', "utf-8")
        config = json.load(fp)
        fp.close()
        fp = codecs.open(self.file_path, 'w', "utf-8")
        config[CONFIG_PARAM_QUEUE_PASSWORD] = password
        json.dump(config, fp, indent=2)
        fp.close()

    def _save_secret(self, password: str):
        fp = codecs.open(self.file_path, 'r', "utf-8")
        config = json.load(fp)
        fp.close()
        fp = codecs.open(self.file_path, 'w', "utf-8")
        config[CONFIG_PARAM_BOT_SECRET] = password
        json.dump(config, fp, indent=2)
        fp.close()

    def renew_if_needed(self):
        if datetime.datetime.now() >= self.next_reload:
            self.logger.debug("Time to reload settings")
            old_file_path = self.old_file_path
            old_db_password = self.db_password
            try:
                self.__init__(self.file_path, reload=True)
                self.reloaded = True
                if self.db_password != old_db_password:
                    self.logger.info("DB password changed, need to reconnect")
                    self.db_credential_changed = True
            except BaseException as exc:
                self.logger.critical("Can't reload settings from new path {0}, error {1}".format(self.file_path, exc))
                self.old_file_path = old_file_path
                self.file_path = old_file_path
        else:
            self.logger.debug("Too early to reload settings")

    def mark_reload_finish(self):
        self.reloaded = False
        self.db_credential_changed = False
