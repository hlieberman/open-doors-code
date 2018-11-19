from HTMLParser import HTMLParser
import logging
import re

import MySQLdb
import sys

log = logging.getLogger()

class Sql(object):

  def __init__(self, args):
    self.tag_count = 0
    db = MySQLdb.connect(args.db_host, args.db_user, args.db_password)
    cursor = db.cursor()
    cursor.execute('CREATE DATABASE IF NOT EXISTS {0}'.format(args.temp_db_database))

    self.db = MySQLdb.connect(args.db_host, args.db_user, args.db_password, args.temp_db_database, charset='utf8',
                              use_unicode=True, autocommit=True)
    self.cursor = self.db.cursor()
    self.database = args.temp_db_database


  def execute(self, script, parameters = ()):
    log.debug("Running SQL {} with params {}".format(script, parameters))
    self.cursor.execute(script, parameters)
    return self.cursor.fetchall()


  def execute_dict(self, script, parameters = ()):
    dict_cursor = self.db.cursor(MySQLdb.cursors.DictCursor)
    dict_cursor.execute(script, parameters)
    return dict_cursor.fetchall()


  def run_script_from_file(self, filename, database, prefix, initial_load = False):
    # Open and read the file as a single buffer
    self.cursor.execute('USE {0}'.format(database))
    fd = open(filename, 'r')
    sqlFile = fd.read()
    fd.close()

    # strip comments, replace placeholders and return all SQL commands (split on ';')
    sqlCommands = sqlFile.replace('$DATABASE$', database).replace('$PREFIX$', prefix).split(';\n')

    # Start a transaction
    self.db.start_transaction()

    # Execute every command from the input file
    for command in sqlCommands:
      # This will skip and report errors
      # For example, if the tables do not yet exist, this will skip over
      # the DROP TABLE commands
      try:
        end_command = re.sub(r'--.*?\n', '', command)
        lc_command = end_command.lower().strip().replace("\n", "")
        if initial_load and (lc_command.startswith("create database") or lc_command.startswith("use ")):
          log.debug("Skipping command - {0}".format(lc_command))
        elif lc_command is None or lc_command == '':
          log.debug("Skipped empty command.")
        else:
          self.cursor.execute(command)
      except MySQLdb.OperationalError, msg:
        log.warn("Command skipped with error: {0} [{1}]".format(command, msg))

    self.db.commit()


  def col_exists(self, col, table, database):
    self.cursor.execute("""
        SELECT * FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = '{0}' AND TABLE_NAME = '{1}' AND COLUMN_NAME = '{2}'
      """.format(database, table, col))
    result = self.cursor.fetchone()
    return not(result is None)

  def create_skeleton(self, database):
    self.cursor.execute("USE {}".format(database))
    self.cursor.execute("""CREATE TABLE IF NOT EXISTS `authors` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `name` varchar(255) NOT NULL DEFAULT '',
    `email` varchar(255) NOT NULL DEFAULT '',
    `imported` tinyint(1) NOT NULL DEFAULT '0',
    `do_not_import` tinyint(1) NOT NULL DEFAULT '0',
    `to_delete` tinyint(1) DEFAULT '0',
    PRIMARY KEY (`id`),
    UNIQUE KEY `id_UNIQUE` (`id`)
    ) DEFAULT CHARSET=utf8""")
    self.cursor.execute("""CREATE TABLE IF NOT EXISTS `chapters` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `position` int(11) DEFAULT NULL,
    `title` varchar(255) NOT NULL DEFAULT '',
    `authorID` int(11) NOT NULL DEFAULT '0',
    `text` mediumtext,
    `date` datetime DEFAULT NULL,
    `story_id` int(11) DEFAULT '0',
    `notes` text,
    `url` varchar(1024) DEFAULT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `id_UNIQUE` (`id`),
    KEY `storyid` (`story_id`)
    ) DEFAULT CHARSET=utf8""")
    self.cursor.execute("""CREATE TABLE IF NOT EXISTS `stories` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `title` varchar(255) NOT NULL DEFAULT '',
    `summary` text,
    `notes` text,
    `author_id` int(11) DEFAULT '0',
    `rating` varchar(255) NOT NULL DEFAULT '',
    `date` datetime DEFAULT NULL,
    `updated` datetime DEFAULT NULL,
    `categories` varchar(45) DEFAULT NULL,
    `tags` varchar(255) NOT NULL DEFAULT '',
    `warnings` varchar(255) DEFAULT '',
    `fandoms` varchar(255) DEFAULT NULL,
    `characters` varchar(255) DEFAULT NULL,
    `relationships` varchar(255) DEFAULT NULL,
    `url` varchar(255) DEFAULT NULL,
    `imported` tinyint(1) NOT NULL DEFAULT '0',
    `do_not_import` tinyint(1) NOT NULL DEFAULT '0',
    `ao3_url` varchar(255) DEFAULT NULL,
    `import_notes` varchar(1024) DEFAULT '',
    `coauthor_id` int(11) DEFAULT '0',
    PRIMARY KEY (`id`),
    UNIQUE KEY `id_UNIQUE` (`id`),
    KEY `authorId` (`author_id`)
    ) DEFAULT CHARSET=utf8;""")
    self.cursor.execute("""CREATE TABLE IF NOT EXISTS `story_links` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `title` varchar(255) CHARACTER SET latin1 NOT NULL DEFAULT '',
    `summary` text,
    `notes` text,
    `author_id` int(11) DEFAULT '0',
    `rating` varchar(255) CHARACTER SET latin1 NOT NULL DEFAULT '',
    `date` date DEFAULT NULL,
    `updated` datetime DEFAULT NULL,
    `categories` varchar(45) DEFAULT NULL,
    `tags` varchar(255) NOT NULL DEFAULT '',
    `warnings` varchar(255) DEFAULT '',
    `fandoms` varchar(255) DEFAULT NULL,
    `characters` varchar(255) DEFAULT NULL,
    `relationships` varchar(255) DEFAULT NULL,
    `url` varchar(255) DEFAULT NULL,
    `imported` tinyint(1) NOT NULL DEFAULT '0',
    `do_not_import` tinyint(1) NOT NULL DEFAULT '0',
    `ao3_url` varchar(255) DEFAULT NULL,
    `broken_link` tinyint(1) NOT NULL DEFAULT '0',
    `import_notes` varchar(1024) DEFAULT '',
    PRIMARY KEY (`id`),
    UNIQUE KEY `id_UNIQUE` (`id`),
    KEY `authorId` (`author_id`)
    ) DEFAULT CHARSET=utf8;""")
